# Design: Measurement Calibration

## Technical Approach

Replace `threshold_pct=0.001` with ATR-based measurement in `MarketStateTracker`, enrich `ExecutionResult` with strategy state for Reflection Clock snapshot persistence, add `created_by` to `strategy_snapshots`. All changes within existing 4 clocks.

## Architecture Decisions

| Decision | Option | Tradeoff | Choice |
|---|---|---|---|
| **ATR computation** | a) Full OHLC ATR from tick windows | Accurate but complex — requires high/low extraction from N-tick windows | **b) mean absolute price change** — simpler, deterministic, same effect |
| | **b) mean of N absolute price changes** | Simple, pure arithmetic, directly usable as per-tick volatility measure | |
| **ATR ownership** | a) New StateGenerator | Overengineering — two classifiers with one threshold | **b) ATRCalculator helper** — both MarketStateTracker and DirectionalStateGenerator consume it |
| | **b) ATRCalculator helper class** | Single source of truth for τ, shared by both classifier implementations | |
| **ExecutionResult enrichment** | a) ReflectionEngine queries DB for transition matrix | Breaks C6 (clock boundary), adds DB dependency to reflection | **b) Engine populates snapshot field** — clean data flow, strategy → ExecutionResult → ReflectionEngine |
| | **b) Engine populates `strategy_snapshot` field | Direct handoff, no DB query in reflection | |
| **classified_state location** | a) event_store (per REQ-MC-004) | Architecture tension: classification occurs in EXECUTING, not CAPTURING. event_store is written during CAPTURING — populating `classified_state` at capture is impossible without merging stages | **b) execution_log.state** — already stores classified state at execution time. No schema change. REQ-MC-004 satisfied by existing column. |
| | **b) execution_log.state (already exists)** | No code change, atomically written with each tick during engine step 7 | |

## Data Flow

```
CAPTURING:  adapter → event_store (raw ticks, no classification)
EXECUTING:  event_store → normalize → MarketStateTracker(ATR) → strategy → ExecutionResult
                                                        └─ snapshot_data
REFLECTING: ExecutionResult ─→ ReflectionEngine.reflect(execution_result=result)
                                      └─ persist_snapshot(db, created_by="reflection_engine")
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/trady_ai/core/state.py` | Modify | `ATRCalculator` class added; `MarketStateTracker` accepts `alpha`, `atr_period`, computes τ per tick |
| `src/trady_ai/core/engine.py` | Modify | `ExecutionResult` gains `strategy_snapshot: dict \| None`; engine populates it after run loop |
| `src/trady_ai/strategies/markov/state_generator.py` | Modify | `DirectionalStateGenerator` accepts optional `ATRCalculator` for threshold alignment |
| `src/trady_ai/core/persistence.py` | Modify | `strategy_snapshots` schema: ADD `created_by TEXT NOT NULL DEFAULT 'strategy'`; `persist_strategy_snapshot` accepts `created_by` param. `RuntimeConfig`: add `alpha=2.0`, `atr_period=20` |
| `src/trady_ai/config/runtime_config.py` | Modify | Add `alpha: float = 2.0`, `atr_period: int = 20` |
| `src/trady_ai/strategies/markov/persistence.py` | Modify | `snapshot()` deprecated: emits `DeprecationWarning`, returns data dict without DB write; `on_snapshot()` unchanged |
| `src/trady_ai/reflection/engine.py` | Modify | `reflect()` accepts `execution_result` param; new `persist_snapshot(result)` step after calibration analyzer, before report assembly |
| `src/trady_ai/paper_trading/session.py` | Modify | `_do_execute` returns `ExecutionResult`; `_do_reflect` receives it; session never imports `persist_strategy_snapshot` |
| `src/trady_ai/paper_trading/bundler.py` | Modify | Include `strategy_snapshot.json` in bundle when present |
| `Papertrading review/PAPER-TRADING-ARCHITECTURE-CONTRACT.md` | Modify | §28: v2.0→v2.1 entry; §29: D-003 documented |

## Interfaces / Contracts

**ATRCalculator**:
```python
class ATRCalculator:
    def __init__(self, alpha: float = 2.0, period: int = 20, buffer_size: int = 1000)
    def update(self, market_id: str, price: Decimal) -> Decimal | None  # → τ or None (first tick)
    def threshold(self, market_id: str) -> Decimal  # → computed τ
    def clear(self, market_id: str) -> None
```

**ReflectionEngine.reflect signature change**:
```python
def reflect(self, scope, domain, mode, ..., execution_result: ExecutionResult | None = None) -> ReflectionReport
```

**Session boundary**: AST-level check confirms `session.py` does not import `persist_strategy_snapshot`. Contract check via `validate_isolation_boundary()` extended.

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | ATRCalculator: buffer ops, first-tick=NEUTRAL, deterministic | New `TestATRCalculator` |
| Unit | MarketStateTracker: UP/DOWN/NEUTRAL with variable τ | Update tests: assert state labels, not constants |
| Unit | DirectionalStateGenerator: consistency with MarketStateTracker | Same ATR config → same classification |
| Unit | ReflectionEngine: persist_snapshot provenance + idempotency | New `TestReflectionSnapshot` |
| Integration | Full session: execute→snapshot→reflect | New `TestSessionReflectionFlow` |
| Governance | calibrate review: min/max/mean τ display | Update `TestCalibrateReview` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundaries changed.

## Migration / Rollout

- **Additive schema**: `ALTER TABLE strategy_snapshots ADD COLUMN created_by TEXT NOT NULL DEFAULT 'strategy'` — no data migration
- **Config-driven rollback**: set `alpha=0.0` or `threshold_pct=0.001` in RuntimeConfig → original behavior
- **VPS 55+ sessions**: existing snapshots unchanged; new rows get `created_by="reflection_engine"`
- **Running experiment continues**: ATR threshold applied from next `run_session`

## Open Questions

- [ ] REQ-MC-004 insists event_store carries `classified_state`, but classification happens in EXECUTING (not CAPTURING). `execution_log.state` already stores classified state per tick atomically. Confirm whether execution_log satisfies this requirement or if event_store backfill is required.
- [ ] Pre-Day-0 calibration pilot needs testnet data to determine optimal N and α. Recommended: N=20 (20 ticks of 1-second Bybit data ≈ 20-second volatility window), α=2.0 (default from REQ-MC-002). Operator-adopted after pilot.
