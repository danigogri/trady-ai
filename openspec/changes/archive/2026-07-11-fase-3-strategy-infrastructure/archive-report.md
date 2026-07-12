# Archive: Fase 3 — Strategy Infrastructure (Markov Persistence Engine)

**Close date**: 2026-07-11

## Executive Summary

Fase 3 formalizes strategies as isolated first-class modules, migrating `MarkovStrategy` from `core/` into `strategies/markov/persistence.py` as `MarkovPersistenceEngine` with SQLite-persisted 3×3 transition matrices. Introduced `StrategyBase` (refines `SignalStrategy`), `StrategyRegistry` (dict + factory), and two V1 Markov variants (`DirectionalPersistence`, `VolatilityPersistence`). All 199 existing tests pass via backward-compat re-export stub in `core/markov_strategy.py`.

The change was delivered as 3 chained PRs (stacked-to-main) via the `feat/fase-3-strategy-infrastructure` branch. Final verification: 284 tests, 92.40% coverage, 0 mypy + 0 ruff errors.

## Artifacts Archived

| Artifact | Archive File | Source |
|----------|-------------|--------|
| **Proposal** | `proposal.md` | `openspec/changes/fase-3-strategy-infrastructure/proposal.md` |
| **Spec** | `spec.md` | `openspec/changes/fase-3-strategy-infrastructure/spec.md` |
| **Design** | `design.md` | `openspec/changes/fase-3-strategy-infrastructure/design.md` |
| **Tasks** | `tasks.md` | `openspec/changes/fase-3-strategy-infrastructure/tasks.md` |
| **Verify Report** | `verify-report.md` | `openspec/changes/fase-3-strategy-infrastructure/verify-report.md` |
| **Archive Report** | `archive-report.md` | *(current)* |

### Delta Specs Synced to Main

| Domain | Action | Main Spec Path |
|--------|--------|----------------|
| strategy-infrastructure | **Created** (NEW) | `openspec/specs/strategy-infrastructure/spec.md` |
| markov-persistence-engine | **Created** (NEW) | `openspec/specs/markov-persistence-engine/spec.md` |
| 002-deterministic-core | **Created** (delta → full spec) | `openspec/specs/002-deterministic-core/spec.md` |

## Final Verification Metrics

| Metric | Result | Threshold |
|--------|--------|-----------|
| Tests | 284/284 pass | ≥ 90% coverage |
| Coverage | 92.40% | ≥ 90% |
| ruff | 0 errors | 0 |
| mypy (strict) | 0 errors (33 source files) | 0 |
| Spec requirements | 32/32 ✅ | 32/32 |
| Design decisions | 11/11 ✅ | 11/11 |
| Acceptance criteria | 12/12 ✅ | 12/12 |
| Tasks completed | 14/14 | 14/14 |

### Spec Compliance

| Domain | Requirements | Status |
|--------|-------------|--------|
| Strategy Infrastructure | R1–R6 (15 scenarios) | 15/15 ✅ |
| Markov Persistence Engine | R1–R6 (11 scenarios) | 11/11 ✅ |
| 002-Deterministic Core (Delta) | 8 scenarios | 8/8 ✅ |

## Files Changed

### Source — Created (5 files)

| File | Lines | Purpose |
|------|-------|---------|
| `src/trady_ai/strategies/__init__.py` | 15 | Export `StrategyBase`, `StrategyRegistry` |
| `src/trady_ai/strategies/base.py` | 130 | `StrategyBase(SignalStrategy, ABC)` — fail-fast, lifecycle hooks |
| `src/trady_ai/strategies/registry.py` | 86 | `StrategyRegistry` — dict + factory, singleton per key |
| `src/trady_ai/strategies/markov/__init__.py` | 19 | Export `MarkovPersistenceEngine`, `DirectionalPersistence`, `VolatilityPersistence` |
| `src/trady_ai/strategies/markov/persistence.py` | 317 | `MarkovPersistenceEngine` + `DirectionalPersistence` + `VolatilityPersistence` |

### Source — Modified (3 files)

| File | Change |
|------|--------|
| `src/trady_ai/core/persistence.py` | +92 lines: `init_strategy_tables()`, `persist_strategy_snapshot()`, `load_latest_snapshot()` |
| `src/trady_ai/core/markov_strategy.py` | Replaced 94-line class with 2-line re-export stub |
| `src/trady_ai/core/__init__.py` | Removed direct `MarkovStrategy` re-export (prevents circular import) |

### Tests — Created (8 files, 1242 lines)

| File | Lines | Purpose |
|------|-------|---------|
| `tests/unit/strategies/test_base.py` | 195 | ABC enforcement, non-MarketState TypeError, warmup signal, isolation |
| `tests/unit/strategies/test_registry.py` | 233 | Singleton per key, cross-domain isolation, KeyError, list, reset |
| `tests/unit/strategies/markov/conftest.py` | 17 | Shared fixtures for markov tests |
| `tests/unit/strategies/markov/test_markov_engine.py` | 553 | Engine core, DirectionalPersistence, VolatilityPersistence, signal contract, fail-fast |
| `tests/unit/strategies/markov/test_persistence_schema.py` | 94 | Schema idempotence, snapshot/restore, append-only invariant, corrupt JSON |
| `tests/unit/strategies/test_backward_compat.py` | 41 | Legacy import paths, SignalStrategy IS-A, constructor compat |
| `tests/integration/strategies/__init__.py` | 0 | Package marker |
| `tests/integration/strategies/test_engine_via_registry.py` | 109 | Registry-vs-direct identical results, warmup preserved |

## Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Inheritance | `StrategyBase(SignalStrategy, ABC)` | Engine depends on `SignalStrategy` — must be IS-A |
| Registry | Dict[domain, dict[name, instance]], factory on register | Simple, avoids over-engineering (proposal risk accepted) |
| Variants | Independent subclasses of `MarkovPersistenceEngine` | Different state spaces (UP/DOWN vs HIGH/LOW), different output semantics |
| Snapshot storage | Full 3×3 matrix JSON, append-only | Simplifies restore; no state reconstruction needed |
| Domain assignment | Post-creation via `instance.domain = val` (set by registry) | Preserves backward-compat constructor signature |
| Re-export strategy | `core/markov_strategy.py` stub bypasses `core/__init__.py` | Prevents circular import between `strategies/` → `core/` → `strategies/` |

## Backlog Items Registered

| ID | Type | Severity | File | Status |
|----|------|----------|------|--------|
| BL-018 | deuda | baja | `strategies/markov/persistence.py:192` | **abierto** |

### BL-018 — `_last_state` not persisted in snapshot

`restore()` sets `_last_state = None`. The snapshot schema has no `last_state` column. This means the first `update()` after restore does not record a transition from the previous state (1 data point lost per restore cycle). All tests pass because `evaluate()` depends only on `_transition_counts`.

**Fix deferred**: Requires adding `last_state TEXT` column to `strategy_snapshots` table + roundtrip tests with transitions. Low impact — evaluate() unaffected.

## Acceptance Criteria Checklist

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `strategies/` package exports base, registry, Markov Persistence Engine | ✅ |
| 2 | Engine-via-registry produces identical results to Fase 2 (determinism test) | ✅ |
| 3 | Transition snapshots persist to SQLite and restore deterministically | ✅ |
| 4 | 199 existing tests pass unchanged (backward-compat re-export) | ✅ |
| 5 | New module ≥90% coverage, mypy 0 errors, ruff clean | ✅ (92.40%, 0, 0) |
| 6 | `warmup_ticks`/`is_ready()` preserved | ✅ |
| 7 | Signal is NEVER an execution command — core decides execution | ✅ |
| 8 | Strategies consume ONLY core/ normalized contracts (MarketState, Signal) | ✅ |
| 9 | No strategy imports from adapters/, governance/, reflection/ | ✅ |
| 10 | Fail-fast: no silent degradation, no hidden fallback, no invisible recalibration | ✅ |
| 11 | Each (domain, name) pair gets isolated instance — no cross-contamination | ✅ |
| 12 | Statistical traceability: signal lineage + parameter lineage + evaluation lineage persisted | ✅ |

## Issues Found

| Severity | Count | Details |
|----------|-------|---------|
| CRITICAL | 0 | — |
| WARNING | 0 | — |
| SUGGESTION | 1 | BL-018: `_last_state` not persisted (deferred) |

## Deferred Items

| Item | Reason | Target |
|------|--------|--------|
| BL-018: `_last_state` column in `strategy_snapshots` | Impact is minimal (1 data point per restore cycle), `evaluate()` unaffected | Future persistence layer evolution |

## Lessons Learned

1. **Chained PRs worked for 880+ lines**: Splitting into 3 PRs (~200, ~380, ~300 lines) kept each review under the 400-line budget. The `stacked-to-main` strategy is effective for medium-large changes.

2. **BL-018 as architectural debt**: The verify report SUGGESTION identified a gap between the ideal snapshot contract (total resumability) and the pragmatic implementation. Registered as BL-018 and deferred — good discipline to document but not block archive.

3. **Circular import prevention**: The re-export stub in `core/markov_strategy.py` (bypassing `core/__init__.py`) was the correct fix for the `strategies → core → strategies` cycle. Documented in delta spec for future reference.

4. **Delta specs now follow convention**: Unlike Fase 2 (which placed artifacts directly in `openspec/specs/`), this change correctly placed delta specs in `openspec/changes/fase-3-strategy-infrastructure/specs/{domain}/`. The archive syncs them to `openspec/specs/{domain}/` as main specs.

## Next Steps (Orchestrator)

1. **Squash WIP commit** (`7093275`) into a clean commit: `feat: Fase 3 — Strategy Infrastructure (284 tests, 92.40%, 0 mypy, 0 ruff)`
2. **Push** to remote (`feat/fase-3-strategy-infrastructure`)
3. **Create PR** on GitHub with diff summary, verification metrics, and checklist
4. **Close BL-018** as deferred in BACKLOG.md (keep open with rationale)

## Verdict

**APPROVED — ARCHIVED** ✅

The change "Fase 3 — Strategy Infrastructure (Markov Persistence Engine)" is complete, verified, and archived:

- 14/14 tasks implemented ✅
- 284/284 tests pass (284 > 199 baseline) ✅
- 92.40% coverage (≥ 90% threshold) ✅
- 0 errors mypy + ruff ✅
- 32/32 spec requirements compliant ✅
- 11/11 design decisions implemented ✅
- 12/12 acceptance criteria met ✅
- 0 CRITICAL, 0 WARNING issues ✅
- 1 SUGGESTION (BL-018) deferred with rationale ✅
- Zero regressions in Fase 1 + Fase 2 ✅
