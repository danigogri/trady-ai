# Tasks: Measurement Calibration

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 410–460 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Scope | PR | Focused test | Rollback boundary |
|------|-------|-----|--------------|-------------------|
| 1 | ATRCalculator + MarketStateTracker + contract | PR 1 | `pytest tests/unit/test_state.py tests/unit/strategies/markov/test_state_generator.py -q` | Revert ATRCalculator + config; old threshold_pct path intact |
| 2 | ExecutionResult + Reflection + Session + Schema + Bundler | PR 2 | `pytest tests/unit/test_reflection_engine.py -q` | Revert created_by column + session/engine/reflection wiring |
| 3 | Regression + calibrate review + mypy/ruff | PR 3 | `pytest tests/unit/ tests/integration/ -q` | All gates pass; single PR |

---

## Phase 1: ATR Foundation

- [x] 1.1 RED: `tests/unit/strategies/markov/test_atr_calculator.py` — first-tick-None, empty buffer, buffer limit, identity, deterministic τ
- [x] 1.2 GREEN: `src/trady_ai/strategies/markov/atr_calculator.py` — `ATRCalculator(alpha, period, buffer_size)` + `update`, `threshold`, `clear`
- [x] 1.3 RED: `tests/unit/test_state.py` — MarketStateTracker with ATR classifies UP/DOWN/NEUTRAL; first tick NEUTRAL; spike adapts within N
- [x] 1.4 GREEN: `src/trady_ai/core/state.py` — add `alpha=2.0, atr_period=20` to ctor alongside `threshold_pct=0.001` (backward-compat); τ = α × atr / price
- [x] 1.5 GREEN: `src/trady_ai/config/runtime_config.py` — add `alpha: float = 2.0`, `atr_period: int = 20`
- [x] 1.6 GREEN: `Papertrading review/PAPER-TRADING-ARCHITECTURE-CONTRACT.md` — §28: v2.0→v2.1; §29: D-003 recalibration

## Phase 2: Reflection Snapshot + Schema

- [x] 2.1 RED: `tests/unit/test_reflection_snapshot.py` — snapshot persisted with `created_by="reflection_engine"`; missing `transition_counts` raises ValueError
- [x] 2.2 GREEN: `src/trady_ai/core/engine.py` — `ExecutionResult` gains `strategy_snapshot: dict | None`; populated after run loop from `strategy.on_snapshot()`
- [x] 2.3 GREEN: `src/trady_ai/core/persistence.py` — add `created_by TEXT NOT NULL DEFAULT 'strategy'`; `persist_strategy_snapshot` accepts `created_by` param
- [x] 2.4 GREEN: `src/trady_ai/reflection/engine.py` — `reflect()` accepts `execution_result`; `persist_snapshot(result)` after analyzers, before report
- [x] 2.5 GREEN: `src/trady_ai/paper_trading/session.py` — `_do_execute` returns `ExecutionResult`; `_do_reflect` receives it; no `persist_strategy_snapshot` import
- [x] 2.6 GREEN: `src/trady_ai/paper_trading/bundler.py` — include `strategy_snapshot.json` with SHA-256 in manifest
- [x] 2.7 GREEN: `src/trady_ai/strategies/markov/persistence.py` — `snapshot()` emits DeprecationWarning, returns dict; `on_snapshot()` unchanged

## Phase 3: Integration

- [x] 3.1 GREEN: `src/trady_ai/strategies/markov/state_generator.py` — `DirectionalStateGenerator` accepts optional `ATRCalculator`; consistent with MarketStateTracker
- [x] 3.2 GREEN: `src/trady_ai/paper_trading/contracts.py` — extend `validate_isolation_boundary` to verify no `persist_strategy_snapshot` import

## Phase 4: Regression & Verification

- [x] 4.1 RED: Update 46 test assertions from `threshold_pct=0.001` to state-label assertions (UP/DOWN/NEUTRAL per REQ-MC-013)
- [x] 4.2 GREEN: `pytest tests/unit/ tests/integration/ -q` — 712 passed, 7 pre-existing failures
- [x] 4.3 GREEN: Full regression — `pytest tests/unit/ -q` → 673 passed, 1 pre-existing failure
- [x] 4.4 REFACTOR: `mypy --strict` on changed source files — clean (1 pre-existing error in untracked file)
- [x] 4.5 REFACTOR: `ruff check src/trady_ai/` — All checks passed
