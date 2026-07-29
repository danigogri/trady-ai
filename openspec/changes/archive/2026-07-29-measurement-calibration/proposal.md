# Proposal: Measurement Calibration

> **Baseline**: `paper_trading/CLOSURE-REPORT-2026-07-29.md` — Discovery Phase closed with 7
> validated architectural decisions, 8 rejected alternatives, frozen governance baseline.

## Intent

The Paper Trading experiment produces 99% NEUTRAL states because the frozen 0.1% threshold
is a measurement instrument calibrated for the wrong domain (Polymarket sports). Crypto tick
data operates at 0.001% granularity — two orders of magnitude below the threshold. The
threshold is NOT a strategy parameter (D3); it is Evidence Clock measurement calibration.
This change corrects the measurement methodology, establishes proper clock ownership, and
persists strategy snapshots in the correct architectural location — before the confirmatory
experiment resumes.

*Ref: RFC-004 (Reflection evaluation lineage), RFC-007 (operator sovereignty), Architecture
Contract §28-29 (amendment governance). Roadmap Phase 5.*

## Scope

### In Scope
- Replace fixed 0.1% with ATR-based deterministic threshold, operator-adopted α constant
- Move state classification (UP/DOWN/NEUTRAL) to Evidence Clock conceptually (D2)
- Relocate `strategy_snapshots` persistence from strategy/mid-stream to Reflection Clock's
  REFLECTING stage (D1, D7)
- Add `created_by` provenance column to `strategy_snapshots` — single unified artifact (D5)
- Architecture Contract amendment: §28 Amendment Log entry + §29 Documented Deviation D-003
- Answer design questions Q1-Q12 from closure report §7

### Out of Scope
- New clocks (D4: no fifth clock needed)
- Additional state spaces (C2: three states fixed)
- AI/ML threshold adaptation (C3: deterministic only)
- Mid-experiment threshold changes during confirmatory phase (C4)
- Splitting snapshots into multiple tables (C5)
- Calibration pilot execution (pre-Day-0 calibration is a separate governance activity)

## Capabilities

### New Capabilities
- `measurement-calibration`: ATR-based deterministic threshold computation, operator-adopted
  α, Evidence Clock state classification, and pre-experiment calibration workflow.

### Modified Capabilities
- `paper-trading`: Session REFLECTING stage gains snapshot persistence delegation;
  `strategy_snapshots` column schema amended (`created_by`).
- `strategy-infrastructure`: `persist_strategy_snapshot()` ownership moves from
  strategy's `snapshot()` hook to Reflection Clock orchestration.
- `reflection-systems`: ReflectionEngine gains `persist_snapshot()` responsibility
  consuming ExecutionResult data.

## Approach

**Foundation**: D1-D10 are closed — no further discovery needed. Implementation follows
validated decisions directly. Q1-Q12 are design parameters resolved in specs/design phases.

**Order**: Architecture Contract amendment (§28) MUST precede any code change (GO condition 1).
Amendment documents: threshold methodology change (0.1% → ATR-based), crypto domain
measurement recalibration (D-003), clock ownership reassignment.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/trady_ai/core/state.py` | Modified | MarketStateTracker: threshold → ATR-based; `threshold_pct` replaced |
| `src/trady_ai/core/engine.py` | Modified | ExecutionEngine: state classification conceptually Evidence Clock; tracker init updated |
| `src/trady_ai/strategies/markov/state_generator.py` | Modified | DirectionalStateGenerator: mirrors MarketStateTracker — must stay consistent |
| `src/trady_ai/strategies/markov/persistence.py` | Modified | `snapshot()`: remove direct `persist_strategy_snapshot()` call (D7) |
| `src/trady_ai/core/persistence.py` | Modified | `strategy_snapshots` schema: add `created_by` column; function stays, call site moves |
| `src/trady_ai/reflection/engine.py` | Modified | ReflectionEngine: gains snapshot persistence in `reflect()` pipeline |
| `src/trady_ai/paper_trading/session.py` | Modified | Session delegates snapshot to Reflection, never calls `persist_*` directly |
| `Papertrading review/PAPER-TRADING-ARCHITECTURE-CONTRACT.md` | Modified | §28 amendment entry, §29 D-003 |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing tests assert fixed `threshold_pct=0.001` | High | Impact assessment (Q11) in specs phase; update assertions to ATR-computed values |
| Snapshot relocation breaks reflection/code paths that assume `persist_strategy_snapshot` lives in core persistence | Med | Deprecation path: keep function, move call site; verify with existing 199 tests |
| ATR computation from tick data requires OHLC aggregation | Med | Q4: specs phase determines window (1s/5s) via empirical testnet data |

## Rollback Plan

- ATR-based threshold is configuration: revert `threshold_pct` to 0.001 in RuntimeConfig
  restores original behavior without code rollback
- Snapshot relocation: call site change in one file (`strategy persistence` → `reflection
  engine`); revert is a git checkout of two files
- Schema change: `created_by` column is additive — no migration needed for rollback

## Dependencies

- Architecture Contract amendment (§28, §29, D-003) — MUST complete before any code changes
- Pre-Day-0 calibration data (Bybit testnet sample) — needed to determine ATR period (N) and α

## Success Criteria

- [ ] Architecture Contract v2.1 with §28 amendment entry and §29 D-003 documented
- [ ] ATR-based threshold produces <50% NEUTRAL states (validated against testnet sample)
- [ ] `strategy_snapshots` rows include `created_by = "reflection_engine"`
- [ ] Session never calls `persist_strategy_snapshot()` directly (AST-level contract check)
- [ ] All 199 existing tests pass (updated assertions where justified)
- [ ] `calibrate review` correctly handles variable `threshold_pct` in snapshots (Q12)
- [ ] GO conditions 1-6 satisfied (closure report §9)
