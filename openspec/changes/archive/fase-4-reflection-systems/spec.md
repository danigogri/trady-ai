# Spec: Fase 4 — Reflection Systems (RFC-004)

**Change**: fase-4-reflection-systems
**Capability**: reflection-systems (NEW)
**Deterministic boundary**: 100% deterministic. No LLM, no random seeds. Scheduling and Governance approval are external.

## Modules

| # | Module | Requirements | Scenarios |
|---|--------|-------------|-----------|
| 1 | Reflection Data Model | 3 (report persistence, drift persistence, time-bounded queries) | 4 |
| 2 | Reflection Analyzers | 3 (outcome, signal quality, drift) | 6 |
| 3 | Bounded Proposal Generator | 2 (range enforcement, lifecycle) | 4 |
| 4 | Trigger Interface | 2 (reflect entry point, engine orchestration) | 4 |
| 5 | Paper Trading Contract | 2 (calibration gate, scale invariance) | 2 |

**Totals**: 12 requirements, 20 scenarios.

## Key Decisions Encoded

- D1: Evidence generation only — no optimization, no production mutation
- D2: Synthetic defaults → 30d Paper Trading → calibration review
- D3: Initiator external — `reflect(scope, domain, mode)` is the fixed contract
- O1: Bounded proposals = parameter adjustments within predefined ranges only
- O2: Threshold-based drift detection (15% default), statistical tests → Fase 5
- O4: 100% deterministic, no LLM in Fase 4

## Full Spec

See `specs/reflection-systems/spec.md` for complete requirements and scenarios.
