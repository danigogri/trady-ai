# Proposal: Fase 5 — Paper Trading (Operational Phase)

## Intent

Formalize the 30-day dry_run operational window that produces auditable evidence for Governance calibration review. The system already has all required capabilities (capture, execute, reflect). This proposal defines **how the operator runs it** day-to-day.

## Scope

### In Scope
- `PaperTradingSession` operational sequencing component at `src/trady_ai/paper_trading/`
- CLI command `trady-ai paper-trade session` that sequences capture → run → reflect → verify
- Operational contract validation (dry_run enforcement, evidence completeness)
- Per-session evidence bundling + manifest generation
- 30-day lifecycle formalization (start gate, daily ops, end gate)
- Progress tracking: day N/30, sessions completed, artifact completeness

### Out of Scope
- ❌ New analyzers or reflection capabilities (Fase 4 scope)
- ❌ LLM/Intelligence integration (Fase 5 proper)
- ❌ Governance automation (Fase 7)
- ❌ Hermes automation (Fase 8)
- ❌ Temporary scripts that won't survive into production

## Capabilities

### New Capabilities
- `paper-trading`: Operational sequencing of capture → run → reflect → verify cycle. Owns session coordination only. Introduces no new business logic, analytical capabilities, governance authority, or execution authority.

### Modified Capabilities
- None — reflection-systems (calibration gate, scale invariance) and polymarket-integration (dry_run execution) already spec'd. This phase consumes them as-is.

## Approach

Lightweight module at `src/trady_ai/paper_trading/`:

| File | Responsibility |
|------|---------------|
| `session.py` | `PaperTradingSession` — operational sequencer, coordinates services via direct Python import (no subprocess) |
| `contracts.py` | Validate dry_run mode, evidence completeness, temporal integrity |
| `bundler.py` | Package session artifacts into structured evidence bundle + manifest |
| `models.py` | `SessionReport`, `SessionManifest`, `ContractViolation`, `SessionState` |

CLI at `trady-ai paper-trade session --scope daily --domain PM-5M`. The coordinator is reusable by any initiator — CLI today, Hermes tomorrow.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/trady_ai/paper_trading/` | New | Orchestration module (session, contracts, bundler, models) |
| `src/trady_ai/cli/main.py` | Modified | Add `paper-trade` command group |
| `openspec/specs/paper-trading/` | New | Paper trading capability spec |

## Operational Isolation Contract

PaperTradingSession is an operational sequencing component. It owns session coordination only. It introduces no new business logic, analytical capabilities, governance authority, or execution authority.

### Authority Boundaries (MUST NOT)

| # | Prohibition | Owned By |
|---|-------------|----------|
| 1 | MUST NOT make strategy or execution decisions | Core / Intelligence |
| 2 | MUST NOT interpret market data or signal quality | Reflection |
| 3 | MUST NOT modify signals, parameters, or thresholds | Intelligence |
| 4 | MUST NOT generate or evaluate strategy proposals | Reflection / Governance |
| 5 | MUST NOT perform reasoning or optimization | Intelligence |
| 6 | MUST NOT assume governance authority over deployments | Governance |

### Enforcement

Each prohibition is enforced in `contracts.py` via explicit validation checks. Any violation returns a `ContractViolation` with severity CRITICAL, halting the session.

### Future Compatibility

This contract is designed to survive into Hermes automation (Fase 8) without modification. Hermes replaces the human operator as initiator, but the sequencer's authority boundaries remain unchanged.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Sequencer absorbs decision authority | Medium | Enforced via Operational Isolation Contract — 6 categorical MUST NOT rules, each validated per session |
| Evidence gaps from missed days | Low | Time gate requires 30 DISTINCT days, not consecutive |
| dry_run accidentally disabled | Critical | `validate_execution_secrets()` gates every session pre-flight |
| Module becomes fat layer | Low | Size budget: <500 lines total, <100 per file |

## Rollback Plan

1. Remove `paper-trading/` directory
2. Revert CLI changes in `main.py`
3. Archive evidence bundles or delete ephemeral data
4. No migration needed — no new tables, no schema changes

## Dependencies

- `reflection-systems` spec — calibration gate module (already exists)
- `003-polymarket-integration` spec — dry_run execution (already exists)
- RFC-000 (Safety), RFC-004 (Reflection) — frozen, compatible

## Success Criteria

- [ ] `trady-ai paper-trade session` runs full capture → run → reflect → verify cycle
- [ ] Contract validation catches disabled dry_run before execution
- [ ] Evidence bundle contains: session report, manifest, artifact checksums
- [ ] All existing tests pass (no regressions)
- [ ] Module is <500 lines total
