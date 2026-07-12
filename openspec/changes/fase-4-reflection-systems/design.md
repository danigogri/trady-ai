# Design: Fase 4 — Reflection Systems (RFC-004)

## Technical Approach

Stateless analyzers consuming time-bounded DB queries produce deterministic evidence for a bounded proposal generator. `ReflectionEngine` orchestrates: scope resolution → 3 analyzers → proposal gen → persistence. Reads Core tables only; writes to `reflection_reports`, `drift_events`, `proposals`.

## Architecture Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| ADR-1 | Analyzer state | Stateless (DB injected per call) | Pure functions are composable, testable, reproducible |
| ADR-2 | Report schema | JSON blob in `report_data` | Report shape evolves; JSON avoids migration churn |
| ADR-3 | Execution timing | Post-execution only | RFC-004: reflection observes, never blocks pipeline |
| ADR-4 | Drift method | Threshold-based (15% default) | Deterministic, explainable. Statistical tests → Fase 5 |
| ADR-5 | Proposal scope | Parameter ranges only | Boundedness per O1 — warmup_ticks [10,200], threshold_pct [0.0001, 0.01] |
| ADR-6 | Snapshot compare | Two explicit ticks: `baseline_tick`, `comparison_tick`; default latest-two when None | Precise contract; direction-explicit naming; same cost as hardcoded LIMIT 2 |

## Module & Class Design

```
src/trady_ai/reflection/
├── engine.py              # ReflectionEngine(db, analyzers*, proposal_gen)
├── models.py              # ReflectionReport, DriftEvent, Proposal dataclasses
├── analyzers/
│   ├── outcome.py         # OutcomeAnalyzer.analyze(db, domain, start, end) → OutcomeSummary
│   ├── signal_quality.py  # SignalQualityAnalyzer.analyze(...) → SignalQualityReport
│   └── drift.py           # DriftAnalyzer.analyze(db, strategy_id, domain, baseline_tick=None, comparison_tick=None) → list[DriftEvent]
├── proposals/generator.py # generate(current_params, drift_events) → list[Proposal]
└── persistence.py         # save_report(), save_drift(), save_proposals(), query helpers
```

All analyzers are stateless (no constructor state, DB passed as param). `ReflectionEngine` takes `Database` + analyzer instances via constructor injection — same pattern as `ExecutionEngine`.

## Data Flow & Sequence

```
reflect("session","PM-5M","dry_run")
  │
  ▼ ReflectionEngine
  ├─→ OutcomeAnalyzer.analyze()  ── query trades/positions ──→ OutcomeSummary
  ├─→ SignalQualityAnalyzer.analyze() ── query signals ──→ SignalQualityReport
  ├─→ DriftAnalyzer.analyze(db, strategy_id, domain, baseline_tick, comparison_tick) ── snapshots×2 ──→ list[DriftEvent]
  ├─→ ProposalGenerator.generate(current_params, drift_events) ──→ list[Proposal]
  └─→ persist: INSERT reflection_reports + drift_events + proposals
  ──→ return ReflectionReport
```

Analyzers run sequentially (deterministic order). Drift events feed ProposalGenerator. Engine calls persistence last.

## Database Schema

| Table | Key Columns |
|-------|-------------|
| `reflection_reports` | id PK, scope (session/daily/weekly), domain, mode, period_start, period_end, report_data (JSON), created_at |
| `drift_events` | id PK, strategy_id, domain, metric, previous_value, current_value, threshold, deviation_pct, detected_at, acknowledged (INT 0/1) |
| `proposals` | id PK, strategy_id, parameter_name, current_value, proposed_value, range_min, range_max, justification, status (draft/submitted), created_at |
| `reflection_config` | domain TEXT, key TEXT, value TEXT, updated_at — PK (domain, key) |

**Indexes**: `trades(timestamp)`, `event_store(timestamp)`, `reflection_reports(period_start, period_end)`, `drift_events(strategy_id, domain)`, `proposals(strategy_id)`, `reflection_config(domain)`.

New table initialization added to `core/persistence.py`. Existing table indexes added to `init_core_tables()` — both idempotent.

## Integration Points

| Point | Pattern |
|-------|---------|
| Database | Constructor injection — `ReflectionEngine(db: sqlite_utils.Database, ...)` per `ExecutionEngine` pattern |
| Core queries | Add `query_trades_by_time_range()`, `query_signals_by_time_range()` to `core/persistence.py` |
| Snapshots | `WHERE strategy_name=? AND domain=? AND tick_number IN (baseline_tick, comparison_tick)` or `ORDER BY tick_number DESC LIMIT 2` when ticks are None |
| CLI | Click group `trady-ai reflect {analyze,report,propose}` in `cli/main.py` |
| Config | Reuse `get_settings()` — no new config keys. Per-domain calibration state in `reflection_config` table |

## Calibration Gate State Machine

Per-domain calibration lifecycle with three states stored in `reflection_config(domain, key, value)`:

```
UNCALIBRATED ──→ READY_FOR_CALIBRATION ──→ CALIBRATED
     ↑                                            │
     └──────────── reset_calibration ─────────────┘
```

### Dual gate — both conditions required to reach READY_FOR_CALIBRATION:

1. **Time gate**: `COUNT(DISTINCT DATE(period_start)) >= 30` — at least 30 calendar days with session data
2. **Evidence gate**: `COUNT(session_count) >= min_sessions` — minimum operational sessions with reports

Both must be true. If evidence gate passes but time gate hasn't (e.g., 40 sessions in 5 days), state remains `UNCALIBRATED` — prevents calibration from atypical market regimes.

### Detection: automatic (system evaluates gates on each reflect() call)
### Approval: manual — operator reviews evidence and sets `CALIBRATED` state
### Reset: operator can reset to `UNCALIBRATED` (e.g., after strategy parameter change)

`min_sessions` default: 30. Configurable per domain via `reflection_config(domain, 'min_sessions', value)`.

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Empty trades/signals for range | Analyzers return zeroed defaults (win_rate=0.0, etc.) |
| Only one snapshot exists | DriftAnalyzer returns empty list, drift_detected=false |
| Proposal value out of range | Clamped to boundary; justification notes clamping |
| DB failure | Exception propagates — fail-fast per RFC-000 |

## Determinism Guarantees

- **ORDER BY timestamp ASC** on all analyzer queries
- **No random seeds** — no `random`, no `np.random`
- **No external calls** — pure DB queries + computation
- **Timestamps from DB**, not wall clock (wall clock only for `created_at` attribution)
- **Fixed iteration order** for matrix comparison (0..2 × 0..2), never dict iteration

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Each analyzer | Fixture DB with known rows → assert deterministic output |
| Unit | ProposalGenerator | Clamping at boundaries, within-range passthrough |
| Unit | Engine orchestration | Mock analyzers → assert sequence + report assembly |
| Integration | Full reflect() | Real DB with trades + signals + snapshots → assert persisted reports |

## Configuration vs Knowledge (Conceptual Separation)

Reflection's persistent state falls into two categories. They share `reflection_config` in Phase 4, but future phases may split them:

```
Reflection
├── configuration          (runtime settings)
│   ├── drift_threshold
│   ├── min_sessions
│   └── calibration_state
│
└── knowledge              (deterministic proposal rules)
    └── proposal_rules     (future: discovered by Intelligence, approved by Governance)
```

**Configuration** is operational: thresholds, defaults, calibration state. Set by the operator or auto-detected (calibration gate).

**Knowledge** is analytical: deterministic proposal rules that encode "when condition X, propose adjustment Y." In Phase 4, knowledge is limited to `BOUNDED_PARAMETERS` (hardcoded clamping rules). In future phases, Intelligence (Fase 5) may discover candidate rules from operational evidence, Governance (Fase 7) approves them, and they become active deterministic rules executed by Reflection. This separation is conceptual today; the persistence mechanism may diverge when rule volume warrants it.

### Future Rule Lifecycle (conceptual, not implemented)

Deterministic proposal rules may follow this lifecycle post-Fase 5:

```
DISCOVERED → PROPOSED → UNDER_REVIEW → APPROVED → ACTIVE → DEPRECATED → REMOVED
```

- **DISCOVERED**: Intelligence identifies a candidate rule from operational evidence.
- **PROPOSED**: Rule is serialized and persisted for review.
- **UNDER_REVIEW**: Governance evaluates the rule (boundedness, reversibility, auditability).
- **APPROVED**: Governance approves — rule becomes eligible for execution.
- **ACTIVE**: Reflection executes the rule deterministically in each cycle.
- **DEPRECATED**: Rule is superseded but retained for audit trail.
- **REMOVED**: Rule is archived; no longer executed.

This lifecycle is a long-term governance concept. Phase 4 implements only the subset needed for `BOUNDED_PARAMETERS` clamping rules. Full lifecycle implementation belongs to Fase 7 (Governance Hardening) or a post-Paper-Trading SDD.

## Migration / Rollout

No migration — all new tables, no schema changes. Feature behind CLI only; no automatic scheduling.

## Open Questions

(None — all design decisions resolved before tasks.)
