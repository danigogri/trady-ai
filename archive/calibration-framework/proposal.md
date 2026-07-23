# Proposal: Calibration Framework

**Phase**: 5 — Paper Trading Deployment  
**RFC**: RFC-004 §Reflection Systems, RFC-003 §Markov Infrastructure  
**Research basis**: `MARKOV-STATE-SPACE-METHODOLOGY-2026-07-23.md`, `CALIBRATION-FRAMEWORK-2026-07-23.md`

## Intent

Operationalize the Markov methodology's 4-phase cycle (discovery → definition → validation → refinement) as a deterministic evidence pipeline within the Reflection layer. The current engine hardcodes 3 states — the methodology demands domain-agnostic N-state architecture where state-space adoption is a governed human decision, not a code constant.

## Scope

### In Scope

| Phase | Deliverable |
|-------|-------------|
| **A — Foundation** | `StateGenerator` ABC in `strategies/markov/`, refactor engine from 3×3 to N×N domain-agnostic, relax CHECK constraint |
| **B — Evidence** | `reflection/calibration/` module: AIC, BIC, Markov χ² test, persistence, entropy metrics. Wire into `ReflectionEngine`. CLI `calibrate review` (evidence) and `calibrate adopt` (governance) |

### Out of Scope

- Polymarket adapter, normalization, risk enforcer, session pipeline — no changes
- ML proposal generation (k-means, spectral clustering) — Phase 5+ only
- Hermes/AI integration — postponed per roadmap
- Review window automation (Day 7/14/30 triggers) — manual governance first

## Motivation

1. **Hardcoded 3-state is scientifically invalid.** The methodology report reviewed 6+ disciplines — ZERO prescribe |S|=3. State cardinality is a modeling decision, not an engineering constant.
2. **The methodology IS calibration.** Discovery → definition → validation → refinement maps directly to evidence generation → human review → governance decision.
3. **Paper Trading demands it now.** Without calibration, there is no structured way to evaluate whether a state-space captures real market dynamics during the 30-day experiment.

## Approach

Three bounded contexts (from the calibration framework research):

1. **State Generator abstraction**: `StateGenerator` ABC with `classify(MarketInput) → state_index`. Existing Directional/Volatility become implementations. Engine operates on abstract indices, not hardcoded enums.
2. **Evidence pipeline** (`reflection/calibration/`): Deterministic computation of AIC, BIC, Markov χ², state persistence, and entropy. Generates structured evidence reports. No AI — pure mathematics.
3. **Governance boundary**: `calibrate review` presents evidence. `calibrate adopt` requires explicit human confirmation. The pipeline generates proposals; humans adopt.

## Non-Negotiables

1. Calibration MUST be post-execution (Reflection layer, never execution critical path)
2. State adoption MUST require explicit human action
3. Evidence generation MUST be deterministic (fixed algorithms, no random seeds)
4. Existing tests MUST pass with zero assertion changes
5. Governance boundary between evidence pipeline and adoption MUST be explicit

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Engine refactor breaks existing strategy tests | Medium | Phase A isolated — `StateGenerator` ABC + adapter pattern on existing `DirectionalPersistence`/`VolatilityPersistence` |
| CHECK constraint migration loses data | Low | Migration adds new constraint; old data validated before relaxing old one |
| AIC/BIC misuse (wrong likelihood function) | Medium | Validate against known reference implementations with synthetic P matrices |
| Governance boundary blur over time | Low | `calibrate adopt` is the sole write path; all evidence is read-only |

## Rollback Plan

1. git revert the Phase A+B commits; restore 3×3 CHECK constraint
2. Delete `reflection/calibration/` directory
3. Existing strategies continue operating on hardcoded 3-state engine
4. Zero runtime impact — calibration was never on the execution path

## Dependencies

- **Depends on**: `MARKOV-STATE-SPACE-METHODOLOGY-2026-07-23.md` (scientific foundation), `CALIBRATION-FRAMEWORK-2026-07-23.md` (operationalization), existing `markov-persistence-engine` spec, `reflection-systems` spec
- **Depended on by**: Paper Trading Phase 3 (Day 7/14/30 governance reviews), future multi-domain state-space support (Phase 6+), Hermes analytical assistant (Phase 8)

## Open Questions

1. Does the eigengap heuristic work on Polymarket data with tick-size=0.01?
2. What |S| range is practical for human review at Day 7/14/30?
3. Should evidence reports be SQLite-rows or filesystem artifacts?
4. Minimum observation count for governance decision — Kemeny & Snell say 5/cell; does governance need more?

## Success Criteria

- [ ] Phase A: `DirectionalPersistence` and `VolatilityPersistence` produce identical outputs before and after refactor (existing tests pass with zero assertion changes)
- [ ] Phase A: Engine `update()` and `evaluate()` work for arbitrary |S| ∈ {2,3,4,5,...,N}
- [ ] Phase B: `calibrate review` produces AIC, BIC, Markov χ² p-value, state persistence, and entropy for current state-space
- [ ] Phase B: `calibrate adopt --states 4 --generator volatility` persists adoption decision with provenance metadata
- [ ] Coverage stays ≥ 90%, mypy strict passes, ruff clean
