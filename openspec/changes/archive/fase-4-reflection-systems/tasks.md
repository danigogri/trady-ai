# Tasks: Fase 4 — Reflection Systems

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 550-700 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 (data model) → PR2 (analyzers) → PR3 (engine+proposals) → PR4 (CLI+integration) |
| Delivery strategy | ask-always (resolved: feature-branch-chain) |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Core data model + models + time-bounded queries | PR 1 | Base=feature/tracker branch |
| 2 | OutcomeAnalyzer + SignalQuality + Drift | PR 2 | Base=PR1 branch |
| 3 | ProposalGenerator + ReflectionEngine + persistence | PR 3 | Base=PR2 branch |
| 4 | CLI commands + integration tests | PR 4 | Base=PR3 branch |

## Phase 1: Foundation — Data Model & Queries (PR1)

- [x] T1.1 Create `reflection/models.py` with `ReflectionReport`, `DriftEvent`, `Proposal` dataclasses
- [x] T1.2 Add `init_reflection_tables()` to `core/persistence.py`: `reflection_reports`, `drift_events`, `proposals`, `reflection_config`
- [x] T1.3 Add indexes: `trades(timestamp)`, `event_store(timestamp)`, `reflection_reports(period_start,period_end)`, `drift_events(strategy_id,domain)`, `proposals(strategy_id)`
- [x] T1.4 Add `query_trades_by_time_range()` and `query_signals_by_time_range()` to `core/persistence.py`
- [x] T1.5 Tests: table idempotence, indexes, query helpers return correct time-bounded rows

## Phase 2: Analyzers (PR2)

- [x] T2.1 `OutcomeAnalyzer.analyze(db, domain, start, end)` in `reflection/analyzers/outcome.py` — compute win_rate, total_pnl, avg_pnl, max_drawdown from trades/positions. Empty range → zeroed defaults.
- [x] T2.2 `SignalQualityAnalyzer.analyze(db, domain, start, end)` in `reflection/analyzers/signal_quality.py` — signal_accuracy + confidence_calibration bins.
- [x] T2.3 `DriftAnalyzer.analyze(db, strategy_id, domain, baseline_tick, comparison_tick)` in `reflection/analyzers/drift.py` — compare transition_counts from two snapshots, flag deviations > 15%.
- [x] T2.4 Tests per analyzer: fixture DB with known rows → assert deterministic output, empty ranges, boundary conditions (single snapshot, no drift).

## Phase 3: Proposals & Engine (PR3)

- [x] T3.1 `ProposalGenerator.generate(current_params, drift_events)` in `reflection/proposals/generator.py` — bounded ranges: warmup_ticks [10,200], threshold_pct [0.0001,0.01]. Clamp out-of-range values.
- [x] T3.2 `ReflectionEngine(db, analyzers*, proposal_gen)` in `reflection/engine.py` with `reflect(scope, domain, mode) → ReflectionReport`. Sequential analyzer pipeline + proposal gen + persistence.
- [x] T3.3 Persistence layer in `reflection/persistence.py`: `save_report()`, `save_drift()`, `save_proposals()`, calibration gate queries (dual gate: 30d + min_sessions per domain).
- [x] T3.4 Tests: engine orchestration (mock analyzers), proposal lifecycle draft→submitted, persistence roundtrip, calibration gate state detection.

## Phase 4: CLI & Integration (PR4)

- [x] T4.1 Add Click group `trady-ai reflect {analyze,report,propose}` in `cli/main.py` — each subcommand instantiates ReflectionEngine and renders output.
- [x] T4.2 Integration tests: full `reflect()` roundtrip with real DB (trades + signals + snapshots), CLI output assertions, edge cases (empty DB, single snapshot).
- [x] T4.3 Final verify: mypy src/ --strict clean, ruff check . clean, coverage 92% ≥ 90%, no new `# type: ignore` in reflection module.

## Dependency Graph

```
T1.1─T1.3 → T1.4 ── T1.5
            │
            ├──→ T2.1, T2.2, T2.3 ── T2.4
            │              │
            │              └──→ T3.1 ── T3.2 ── T3.3 ── T3.4
            │                                    │
            │                                    └──→ T4.1 ── T4.2 ── T4.3
            │
            └── (T1.4 feeds all analyzers via query helpers)
```

PR1 = T1.* | PR2 = T2.* | PR3 = T3.* | PR4 = T4.*
