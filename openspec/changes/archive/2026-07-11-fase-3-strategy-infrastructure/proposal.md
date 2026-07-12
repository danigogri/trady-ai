# Proposal: Fase 3 — Strategy Infrastructure (Markov Persistence Engine)

**Roadmap Phase**: 3 | **RFC**: RFC-003-STRATEGY-INFRASTRUCTURE-ARCHITECTURE | **RFC-000**: inherited

## Intent

Fase 3 formalizes strategies as isolated first-class modules — currently ad-hoc in `core/`, bypassing RFC-003 isolation doctrine. Enables independent audit, replacement, and domain-scoping.

## Scope

### In Scope
- `strategies/` package: base classes, registry, lifecycle hooks, isolation contracts
- Markov Persistence Engine V2: SQLite-persisted transition matrix, snapshot/restore, confidence calibration
- Strategy registry: name-based, domain-isolated instances
- Persistence tables: strategy params, matrix snapshots, signal lineage
- TDD: tests before implementation, ≥90% coverage
- Migration: `MarkovStrategy` `core/` → `strategies/markov/` with backward-compat re-export

### Out of Scope
- Other families (momentum, mean reversion). Parameter optimization (Fase 4). Intelligence (Fase 5). Multi-strategy orchestration (Fase 6+).

## Capabilities

### New
- `strategy-infrastructure`: base, registry, lifecycle, isolation enforcement, domain scoping
- `markov-persistence-engine`: 3×3 persisted transition matrix, snapshot/restore, traceability

### Modified
- `002-deterministic-core`: `SignalStrategy` ABC refined → `strategies/base.py`. Engine loads via registry.

## Approach

`core/signal_strategy.py` → `strategies/base.py`. `core/markov_strategy.py` → `strategies/markov/persistence.py`. Engine: registry load → `state → evaluate() → Signal → RiskEnforcer` (unchanged). Each `(domain, name)` gets isolated instance with SQLite-backed state. Transition counts persist after `update()` for replay-independent audit.

## Affected Areas

| Area | Impact |
|------|--------|
| `strategies/` | New |
| `core/signal_strategy.py` | Modified |
| `core/markov_strategy.py` | Removed |
| `core/engine.py` | Modified |
| `core/persistence.py` | Modified |
| `core/__init__.py` | Modified |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Move breaks 199 existing tests | Med | Backward-compat re-export |
| DB complexity from strategy persistence | Low | Append-only snapshots |
| Registry over-engineering | Low | Dict + factory, no IOC |

## Rollback Plan

1. Revert `strategies/`. 2. Restore `core/markov_strategy.py`. 3. Revert `core/signal_strategy.py`, `engine.py`, `persistence.py`. 4. Verify 199 pass, 91% coverage.

## Dependencies

- Fase 1+2 complete. `SignalStrategy` ABC baseline. No new Python deps.

## Success Criteria

- [ ] `strategies/` exported with base, registry, Markov Persistence Engine
- [ ] Engine-via-registry matches Fase 2 results identically
- [ ] Transition snapshots persist to SQLite and restore deterministically
- [ ] All 199 existing tests pass unchanged
- [ ] New module ≥90% coverage, mypy 0 errors, ruff clean
- [ ] `warmup_ticks`/`is_ready()` preserved
