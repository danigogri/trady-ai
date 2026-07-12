# Verification Report: Fase 4 — Reflection Systems

**Date**: 2026-07-12
**Status**: **FAIL** (2 CRITICAL, 3 WARNING, 2 SUGGESTION)

## Summary

| Metric | Result | Threshold |
|--------|--------|-----------|
| Test suite | 367 passed, 0 failed | All pass |
| Reflection tests | 93 tests (all pass) | All pass |
| Coverage | 92% | ≥ 90% |
| mypy strict | 0 errors | Clean |
| ruff | 0 errors | Clean |
| `# type: ignore` in reflection module | 0 | 0 new |
| Pre-existing tests pass | 284+ pre-existing still pass | No regressions |

---

## CRITICAL FINDINGS

### CR-1: Drift-to-Proposal pipeline is non-functional

**Source**: Spec Module 3 (Bounded Proposal Generator), Design ADR-5, Tasks T3.1, Data Flow Diagram

**Requirement**: "Drift events feed ProposalGenerator" — the data flow diagram shows `DriftEvent[]→ ProposalGenerator`. Proposals MUST be generated from drift signals.

**What was found**: `ProposalGenerator.generate()` checks `event.metric in BOUNDED_PARAMETERS`. The bounded parameters are `{"warmup_ticks", "threshold_pct"}`. DriftAnalyzer produces metrics named `transition_0_0` through `transition_2_2`. **No drift event metric can ever match a bounded parameter name.** Therefore, no proposal is ever generated from drift events — the pipeline is dead code.

**Evidence**:
```
Bounded parameters: {'warmup_ticks': [10,200], 'threshold_pct': [0.0001,0.01]}
Drift metrics: 'transition_0_0', 'transition_1_1', 'transition_UP_UP'
→ No match → all drift events silently skipped → proposals always empty from drift
```

- `src/trady_ai/reflection/proposals/generator.py` lines 54-56: `if param_name not in BOUNDED_PARAMETERS: continue`
- `src/trady_ai/reflection/analyzers/drift.py` line 120: `metric=f"transition_{i}_{j}"`
- Unit tests in `test_reflection_engine.py::TestProposalGenerator::test_generates_proposal_for_drift_event` use `metric="warmup_ticks"` — a metric name that DriftAnalyzer never produces, giving **false positive coverage**.

**Recommendation**: Either (a) implement a mapping from transition drift to parameter adjustment (e.g., if `transition_0_0` exceeds threshold, recommend adjusting `threshold_pct` toward midpoint), or (b) document that Fase 4 proposals come from direct parameter analysis only and drift events are informational (update spec and design accordingly).

---

### CR-2: Missing confidence calibration binning

**Source**: Spec Module 2 — SignalQualityAnalyzer, Scenario "Calibrate confidence"

**Requirement**: "confidence_calibration (average predicted confidence vs actual win rate in bins)" — the scenario requires two bins: high-confidence (>0.7) at 80% actual win rate vs low-confidence (≤0.7) at 30% actual win rate.

**What was found**: `SignalQualityAnalyzer` only computes:
- `signal_accuracy` (signals with trades / total signals)
- `avg_confidence` (mean of all confidence values)

No confidence binning is performed. No per-bin win rate computation. The `SignalQualityReport` dataclass has no field for calibration data.

**Evidence**:
- `src/trady_ai/reflection/models.py` lines 36-46: `SignalQualityReport` only has `total_signals`, `signals_with_trades`, `signal_accuracy`, `avg_confidence` — no calibration bins
- `src/trady_ai/reflection/analyzers/signal_quality.py` lines 56-64: Only computes total confidence sum and signal accuracy — no binning logic

**Recommendation**: Add confidence binning to `SignalQualityAnalyzer.analyze()`:
1. Bin signals by confidence ranges ([0, 0.3], (0.3, 0.7], (0.7, 1.0] per spec example)
2. For each bin, compute actual win rate
3. Add `confidence_calibration: dict[str, float]` field to `SignalQualityReport`

---

## WARNING FINDINGS

### W-1: Missing indexes on `trades(timestamp)` and `event_store(timestamp)`

**Source**: Spec Module 1 (Time-Bounded Query Helpers), Spec Module 5 (Scale Invariance), Design Indexes section, Task T1.3

**Requirement**: "An index on `event_store(timestamp)` and `trades(timestamp)` MUST be created." These are required for scale invariance — time-bounded queries must use index scans, not full table scans.

**What was found**: The reflection table indexes are created (`idx_reflection_reports_period`, `idx_drift_events_strategy_domain`, `idx_proposals_strategy_id`, `idx_reflection_config_domain`), but the required indexes on `trades(timestamp)` and `event_store(timestamp)` are **not created** anywhere in `init_core_tables()` or `init_reflection_tables()`.

**Evidence**:
```python
# Current trades indexes: only sqlite_autoindex_trades_1 (PK)
# Current event_store indexes: only sqlite_autoindex_event_store_1 (UNIQUE on event_id)
# No CREATE INDEX ... ON trades(timestamp)
# No CREATE INDEX ... ON event_store(timestamp)
```

**Recommendation**: Add `CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)` and `CREATE INDEX IF NOT EXISTS idx_event_store_timestamp ON event_store(timestamp)` to `init_core_tables()` or `init_reflection_tables()`.

---

### W-2: Tasks.md not updated for T1.1-T2.4

**Source**: Tasks T1.1–T2.4

**Requirement**: All 18 tasks should have their completion status reflected in `tasks.md`.

**What was found**: Tasks T1.1 through T2.4 remain `[ ]` (unchecked) despite all code existing and all tests passing. Tasks T3.1 through T4.3 are correctly marked `[x]`.

| Task | Status in tasks.md | Code exists? | Tests pass? |
|------|-------------------|--------------|-------------|
| T1.1 models.py | `[ ]` | Yes | Yes |
| T1.2 init_reflection_tables | `[ ]` | Yes | Yes |
| T1.3 Indexes | `[ ]` | Partial (4/6) | Partial |
| T1.4 Query helpers | `[ ]` | Yes | Yes |
| T1.5 Tests | `[ ]` | Yes | Yes |
| T2.1 OutcomeAnalyzer | `[ ]` | Yes | Yes |
| T2.2 SignalQualityAnalyzer | `[ ]` | Yes | Partial (CR-2) |
| T2.3 DriftAnalyzer | `[ ]` | Yes | Yes |
| T2.4 Analyzer tests | `[ ]` | Yes | Yes |

**Recommendation**: Update `tasks.md` to reflect actual completion status.

---

### W-3: Drift deviation uses raw counts vs spec probability example

**Source**: Spec Module 2 — DriftAnalyzer scenario

**Requirement**: The spec example shows probability deviation: transition_prob 0.60 → 0.42 = 30% deviation.

**What was found**: The implementation computes deviation on raw transition_counts (integers), not probabilities. For raw counts 100 → 50, deviation = 50%, while if these were probabilities (0.87 → 0.77), the deviation would be ~11%. The 15% threshold applied to raw counts is not equivalent to a 15% probability threshold. This means the calibration gate's "15% default" may need different tuning.

**Recommendation**: Either (a) normalize transition_counts to probabilities before computing deviation (divide each cell by row sum), or (b) document that the 15% threshold applies to raw count relative change, not probability deviation. This is a documentation/calibration issue for Paper Trading phase.

---

## SUGGESTION Findings

### S-1: `_serialize_value` JSON default handler is dead code

**Source**: `src/trady_ai/reflection/persistence.py` lines 22-28

**Finding**: `_serialize_value()` handles `Decimal` and `datetime` types, but is never called because all values are pre-serialized to strings before being added to the `data` dict in `_serialize_report_data()`. This function is unused (0% coverage in lines 24-28 per coverage report).

**Recommendation**: Remove `_serialize_value()` and drop the `default` parameter from `json.dumps()` call.

---

### S-2: ProposalGenerator unit tests use unrealistic metrics

**Source**: `tests/unit/test_reflection_engine.py` lines 19-38

**Finding**: The `_make_drift_event` test helper defaults to `metric="warmup_ticks"` — a metric name that DriftAnalyzer never produces. This gives false confidence that the drift→proposals pipeline works. In reality, DriftAnalyzer produces `transition_X_Y` metrics which never match `BOUNDED_PARAMETERS`.

**Recommendation**: Either (a) add integration-level test that proves proposals are generated from real DriftAnalyzer output (which requires fixing CR-1 first), or (b) rename the test metric to match realistic drift output and document the pipeline limitation.

---

## Verification Results by Module

### Module 1 — Data Model (4 requirements, 4 scenarios)
| Check | Result | Notes |
|-------|--------|-------|
| 4 tables with correct schemas | ✅ PASS | reflection_reports, drift_events, proposals, reflection_config |
| All indexes in place | ⚠️ WARNING | Missing trades(timestamp) and event_store(timestamp) — see W-1 |
| Time-bounded queries | ✅ PASS | query_trades_by_time_range, query_signals_by_time_range |
| Table initialization idempotent | ✅ PASS | Tested by test_init_core_tables_is_idempotent |

### Module 2 — Analyzers (3 requirements, 6 scenarios)
| Check | Result | Notes |
|-------|--------|-------|
| OutcomeAnalyzer deterministic | ✅ PASS | ORDER BY ASC, Decimal arithmetic |
| OutcomeAnalyzer empty data | ✅ PASS | Zeroed defaults returned |
| OutcomeAnalyzer win_rate/PnL/drawdown | ✅ PASS | Correctly computed|
| SignalQualityAnalyzer deterministic | ✅ PASS | ORDER BY ASC |
| SignalQualityAnalyzer empty data | ✅ PASS | Zeroed defaults |
| SignalQualityAnalyzer accuracy/confidence | ✅ PASS | Correct |
| SignalQualityAnalyzer confidence calibration | ❌ FAIL | Missing — see CR-2 |
| DriftAnalyzer deterministic | ✅ PASS | Fixed 3×3 iteration |
| DriftAnalyzer baseline_tick/comparison_tick | ✅ PASS | Both-or-neither validation |
| DriftAnalyzer threshold-based | ✅ PASS | Default 15% |
| DriftAnalyzer < 2 snapshots | ✅ PASS | Empty list |
| DriftAnalyzer single tick | ✅ PASS | ValueError |
| All analyzers stateless | ✅ PASS | DB injected per call |

### Module 3 — Bounded Proposals (2 requirements, 4 scenarios)
| Check | Result | Notes |
|-------|--------|-------|
| warmup_ticks [10, 200] | ✅ PASS | Enforced |
| threshold_pct [0.0001, 0.01] | ✅ PASS | Enforced |
| Clamping at boundaries | ✅ PASS | With justification notes |
| Status "draft" on creation | ✅ PASS | Default in dataclass |
| No strategy swaps | ✅ PASS | Only parameter names in scope |
| No asset changes | ✅ PASS | Only parameter names in scope |
| Drift → Proposal pipeline | ❌ FAIL | See CR-1 |

### Module 4 — Trigger Interface (2 requirements, 4 scenarios)
| Check | Result | Notes |
|-------|--------|-------|
| reflect(scope, domain, mode) → ReflectionReport | ✅ PASS | Correct signature |
| Engine orchestrates analyzers | ✅ PASS | Sequential, deterministic order |
| Writes only to reflection tables | ✅ PASS | No production tables touched |
| Scope resolution works | ✅ PASS | session=1h, daily=24h, weekly=7d |

### Module 5 — Paper Trading Contract (2 requirements, 2 scenarios)
| Check | Result | Notes |
|-------|--------|-------|
| Calibration gate: 3 states | ✅ PASS | UNCALIBRATED → READY_FOR_CALIBRATION → CALIBRATED |
| Dual gate: time (30 days) + evidence | ✅ PASS | Both checked on reflect() |
| Auto-detection of readiness | ✅ PASS | Per _check_calibration_readiness |
| Manual approval for CALIBRATED | ✅ PASS | Set via set_reflection_config |
| Per-domain storage | ✅ PASS | reflection_config table composite PK (domain, key) |

### Architectural Decisions (D1-D3 + O1-O5)
| Check | Result | Notes |
|-------|--------|-------|
| D1: No production mutation | ✅ PASS | Only reflection_* tables written |
| D2: Calibration gate sequence | ✅ PASS | Fase 4 ready → Paper Trading → Calibration |
| D3: Fixed Trigger Interface | ✅ PASS | reflect() contract stable, CLI external |
| O1: Bounded proposals only | ✅ PASS | No strategy swap, no asset change |
| O2: Threshold-based drift (15%) | ✅ PASS | Statistical tests not used |
| O4: 100% deterministic, no LLM | ✅ PASS | No random seeds, no external calls |

### Task Completion (T1.1-T4.3)
| Task | Code | Tests | Status |
|------|------|-------|--------|
| T1.1 models.py | ✅ | ✅ | ⚠️ unchecked in tasks.md |
| T1.2 init_reflection_tables | ✅ | ✅ | ⚠️ unchecked |
| T1.3 Indexes | ⚠️ partial | ✅ | Missing trades/event_store indexes |
| T1.4 Query helpers | ✅ | ✅ | ⚠️ unchecked |
| T1.5 Table/idempotence tests | ✅ | ✅ | ⚠️ unchecked |
| T2.1 OutcomeAnalyzer | ✅ | ✅ | ⚠️ unchecked |
| T2.2 SignalQualityAnalyzer | ✅ | ⚠️ | Missing confidence calibration |
| T2.3 DriftAnalyzer | ✅ | ✅ | ⚠️ unchecked |
| T2.4 Analyzer tests | ✅ | ✅ | ⚠️ unchecked |
| T3.1 ProposalGenerator | ✅ | ✅ | ✅ checked |
| T3.2 ReflectionEngine | ✅ | ✅ | ✅ checked |
| T3.3 Persistence layer | ✅ | ✅ | ✅ checked |
| T3.4 Engine tests | ✅ | ✅ | ✅ checked |
| T4.1 CLI commands | ✅ | ✅ | ✅ checked |
| T4.2 Integration tests | ✅ | ✅ | ✅ checked |
| T4.3 Final verify | ✅ | ✅ | ✅ checked |

### Pre-existing Regressions
| Check | Result | Notes |
|-------|--------|-------|
| All 284+ pre-existing tests pass | ✅ PASS | 367 total tests pass |
| Coverage ≥ 90% | ✅ PASS | 92% |
| No existing functionality broken | ✅ PASS | All commands unchanged |

---

## Conclusion

**Status: FAIL** — 2 CRITICAL issues must be resolved before archive.

### Required fixes before archive:
1. **CR-1**: Fix drift→proposals pipeline — either implement mapping or document as by-design and update spec
2. **CR-2**: Add confidence calibration binning to SignalQualityAnalyzer
3. **W-1**: Add missing indexes on `trades(timestamp)` and `event_store(timestamp)`

### Should fix before archive (recommended):
4. **W-2**: Update `tasks.md` checkboxes
5. **W-3**: Document threshold interpretation (raw counts vs probabilities)

### Archive-ready after fixes? 
**Yes** — after CR-1, CR-2, and W-1 are resolved, the remaining items are documentation/cleanup.
