# Proposal: Fase 4 — Reflection Systems (RFC-004)

**Phase**: Fase 4 | **RFC**: RFC-004 | **Doctrine**: RFC-000 (mandatory inheritance)

## Intent

Introduce bounded post-execution evaluation that transforms deterministic execution history into reproducible evidence for Governance.

## Scope

### In Scope
- New `reflection/` module: analyzers, drift detector, proposal generator, report schemas
- Core data model — `reflection_reports`, `drift_events` tables (time-bounded)
- Basic analyzers: trade outcome, signal quality, win/loss per strategy/domain
- Threshold-based drift detection from strategy `transition_counts` (BL-018 not required)
- Bounded proposal generation: parameter adjustments within predefined ranges only
- Trigger Interface: `reflect(scope, domain, mode) -> ReflectionReport`
- CLI command group: `trady-ai reflect {analyze,report,propose}`
- Scheduling parametrized via Trigger Interface (session/daily/weekly)

### Out of Scope
- Intelligence/LLM integration (→ Fase 5)
- Advanced statistical drift tests (→ Fase 5)
- Strategy swap or asset change proposals
- Autonomous proposal deployment (requires Governance — Fase 7)
- BL-018 fix (low debt, non-blocking)
- Automated scheduling daemon

## Capabilities

### New Capabilities
- `reflection-systems`: trade outcome analysis, signal quality assessment, threshold-based drift detection, bounded proposal generation, reflection report persistence and retrieval

### Modified Capabilities
- None

## Approach

**Option A: Minimal Viable Reflection** — five task groups:

1. **Core data model** — `reflection_reports`, `drift_events` table schemas + time-bounded query helpers in `core/persistence.py`
2. **Analyzers** — outcome analyzer (PnL, win rate per domain/strategy), signal quality analyzer (confidence calibration, direction accuracy), drift analyzer (transition_count deltas)
3. **Proposal generator** — bounded parameter range definition, serialization to DB, proposa status lifecycle (draft → submitted)
4. **Trigger Interface + CLI** — `ReflectionEngine` class with `reflect()` entry point, `trady-ai reflect {analyze,report,propose}` commands
5. **Testing** — unit tests per analyzer, integration tests with real DB, coverage ≥ 90%, mypy strict

100% deterministic (no random seeds). Async/post-execution — reflection never blocks the pipeline.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/trady_ai/reflection/` | New | Analyzers, drift, proposals, report schemas, engine |
| `src/trady_ai/core/persistence.py` | Modified | Time-bounded queries for event_store + signals |
| `src/trady_ai/cli/main.py` | Modified | `reflect` click command group |
| `openspec/specs/reflection-systems/` | New | Spec directory |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Data volume: event_store growth | Med | Time-bounded queries, indexed seq column |
| Determinism: non-reproducible results | Low | No random seeds, ORDER BY on all queries |
| Performance: blocking pipeline | Low | Post-execution only — never in critical path |
| Threshold calibration | Med | Synthetic defaults → recalibrated after 30d Paper Trading (BL-019) |

## Rollback Plan

Reflection is read-only — never mutates production state. Rollback: remove `reflection/` module, revert CLI commands, no data migration. Existing Core tables unaffected.

## Dependencies

- SQLite time-bounded query functions addition to `core/persistence.py`
- Strategy `transition_counts` already persisted (no BL-018 needed)
- RFC-004 doctrinal boundaries (evidence generation, not optimization) — D1, D2, D3

## Security Implications

Per RFC-000: Reflection NEVER mutates production, NEVER holds secrets, NEVER signs transactions. Analysis reads existing DB tables only. No external network access. Secrets isolation doctrine applies bi-directionally — Reflection cannot access secrets, secrets cannot leak into Reflection.

## Success Criteria

- [ ] Analyzers produce deterministic, reproducible reports from event_store + strategy_snapshots
- [ ] Drift detector flags threshold violations from transition_counts
- [ ] Proposal generator creates bounded parameter adjustments only (no strategy swap, no asset change)
- [ ] CLI `reflect` commands produce valid, attributable reflection reports
- [ ] Zero random seed usage (fully deterministic)
- [ ] Coverage ≥ 90%, mypy strict clean, ruff clean

## Delivery Notes

Forecast: significantly exceeds 400 changed lines across all tasks (new module + CLI + tests). Recommended delivery strategy: **feature-branch-chain** with 3-4 chained PRs (data model → analyzers → proposals → CLI). This protects review budget and enables parallel task review.
