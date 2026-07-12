# Spec: Fase 3 — Strategy Infrastructure (Markov Persistence Engine)

**RFC**: RFC-003-STRATEGY-INFRASTRUCTURE-ARCHITECTURE
**Fase**: 3 | **Proposal**: `openspec/changes/fase-3-strategy-infrastructure/proposal.md`
**Baseline**: 001-python-bootstrap + 002-deterministic-core + 003-polymarket-integration
**Mode**: openspec (file-based) | **TDD**: strict (tests before implementation)

---

## Deterministic vs Intelligence Boundary

| Layer | Deterministic | Intelligence |
|-------|--------------|--------------|
| Strategy Base / Registry | ✅ Isolated instances, frozen contracts | ❌ No mutation, no adaptation |
| Markov Persistence Engine | ✅ Transition matrices, argmax, deterministic UUIDs | ❌ No learning, no drift |
| SQLite Persistence | ✅ Append-only snapshots, deterministic restore | ❌ No modification |
| Signal Output | ✅ Structured analytical conclusion | ❌ NOT execution command |

**Invariant**: Strategies evaluate conditions. The deterministic core decides execution (RFC-003 Final Principle).

---

## Data Flow

```
Platform → Adapter (stateless) → MarketInput (normalized contract)
                                        │
                                        ▼
                              MarketStateTracker → MarketState
                                        │
                                        ▼
                          StrategyRegistry.get(domain, name)
                                        │
                                        ▼
                              strategy.update(state)
                              strategy.evaluate(state) → Signal
                                        │
                                        ▼
                              RiskEnforcer → ExecutionDecision
                                        │
                                        ▼
                              ExecutionEngine (core owns authority)
```

---

## Domain Specs

| Domain | Type | Spec Path |
|--------|------|-----------|
| strategy-infrastructure | New | `specs/strategy-infrastructure/spec.md` |
| markov-persistence-engine | New | `specs/markov-persistence-engine/spec.md` |
| 002-deterministic-core | Delta | `specs/002-deterministic-core/delta.md` |

---

## Mandatory Gap Coverage

| Gap | RFC-003 Section | Covered In |
|-----|-----------------|------------|
| G1: Signal as Deterministic Output | §Signal Philosophy | strategy-infrastructure R3, markov-persistence-engine R2 |
| G2: Isolation Barriers | §Isolation Doctrine, §Execution Domain | strategy-infrastructure R1, R2, R4 |
| G3: Fail-Fast Behavior | §Failure Philosophy | strategy-infrastructure R5, markov-persistence-engine R6 |
| G4: Internal Contracts Only | §Relationship With Deterministic Core | strategy-infrastructure R3, markov-persistence-engine R1 |
| G5: Statistical Traceability | §Statistical Traceability | markov-persistence-engine R4, R5 |
| G6: Markov Variants for V1 | §Initial Strategy Focus | markov-persistence-engine R1, R2, R3 |

---

## Acceptance Criteria

- [ ] `strategies/` package exports base, registry, Markov Persistence Engine
- [ ] Engine-via-registry produces identical results to Fase 2 (determinism test)
- [ ] Transition snapshots persist to SQLite and restore deterministically
- [ ] 199 existing tests pass unchanged (backward-compat re-export)
- [ ] New module ≥90% coverage, mypy 0 errors, ruff clean
- [ ] `warmup_ticks`/`is_ready()` preserved
- [ ] Signal is NEVER an execution command — core decides execution
- [ ] Strategies consume ONLY core/ normalized contracts (MarketState, Signal)
- [ ] No strategy imports from adapters/, governance/, reflection/
- [ ] Fail-fast: no silent degradation, no hidden fallback, no invisible recalibration
- [ ] Each (domain, name) pair gets isolated instance — no cross-contamination
- [ ] Statistical traceability: signal lineage + parameter lineage + evaluation lineage persisted
