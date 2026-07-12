# PR #4: Fase 3 — Strategy Infrastructure (Markov Persistence Engine)

**Branch**: feat/fase-3-strategy-infrastructure → main
**Date**: 2026-07-11
**URL**: https://github.com/danigogri/trady-ai/pull/4

---

## What was built

| Module | Lines | Purpose |
|--------|-------|---------|
| `strategies/base.py` | 130 | StrategyBase ABC — isolation, fail-fast, lifecycle hooks |
| `strategies/registry.py` | 86 | StrategyRegistry — dict + factory, singleton per (domain, name) |
| `strategies/markov/persistence.py` | 317 | MarkovPersistenceEngine + DirectionalPersistence + VolatilityPersistence |
| `core/persistence.py` | +92 | init_strategy_tables, persist_snapshot, load_latest_snapshot |
| `core/markov_strategy.py` | stub | Backward-compat re-export |

## Verification

| Gate | Result |
|------|--------|
| pytest | **284 passed** (199 original + 85 new) |
| Coverage | **92.40%** |
| mypy strict | **0 errors** (33 source files) |
| ruff | **All checks passed** |

## Pre-verify fixes applied
- Circular import removed from `core/__init__.py` (re-export via stub only)
- Shadow package `__init__.py` deleted from test dirs
- Test file renamed: `test_persistence.py` → `test_markov_engine.py`

## Known deferred
- **BL-018**: `_last_state` not persisted in strategy_snapshots — 1 transition lost per restore cycle. Architectural debt, negligible functional impact, deferred to future persistence layer evolution.

## Specs archived
`openspec/changes/archive/2026-07-11-fase-3-strategy-infrastructure/`

## Acceptance criteria
- [x] strategies/ exported with base, registry, Markov Persistence Engine
- [x] Engine-via-registry produces identical results to Fase 2
- [x] Transition snapshots persist to SQLite and restore deterministically
- [x] 199 existing tests pass unchanged
- [x] New module ≥90% coverage, 0 mypy, 0 ruff
- [x] warmup_ticks/is_ready() preserved
