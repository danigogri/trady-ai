# Tasks: Fase 3 — Strategy Infrastructure (Markov Persistence Engine)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~880 (source + tests) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Engine) → PR 3 (Persistence + Migration) |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

Each PR stays under 400 lines. PR 1 independent, PR 2 depends on PR 1, PR 3 depends on PR 2.

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Strategy base + registry (base.py, registry.py) | PR 1 → main | Tests included, ~200 lines |
| 2 | MarkovPersistenceEngine core + VolatilityPersistence | PR 2 → main | Depends on PR 1 base, ~380 lines |
| 3 | Persistence schema, snapshot/restore, re-export migration | PR 3 → main | Depends on PR 2 engine, ~300 lines |

## Phase 1: Foundation — Base & Registry [PR 1]

- [ ] 1.1 Write `tests/unit/strategies/test_base.py` — ABC instantiation rejects, non-MarketState TypeError, warmup Signal, no adapter imports
- [ ] 1.2 Create `strategies/base.py` — `StrategyBase(SignalStrategy, ABC)` with `domain`, `parameters()`, `on_init/on_update/on_evaluate/on_snapshot`, fail-fast
- [ ] 1.3 Write `tests/unit/strategies/test_registry.py` — singleton per key, cross-domain isolation, KeyError, list(), reset()
- [ ] 1.4 Create `strategies/registry.py` — `StrategyRegistry` dict+factory, post-creation domain setter
- [ ] 1.5 Update `strategies/__init__.py` — export `StrategyBase`, `StrategyRegistry`
- [ ] Gate: `pytest tests/unit/strategies/` pass, `mypy src/trady_ai/strategies/` clean, `ruff` clean

## Phase 2: Markov Persistence Engine [PR 2]

- [ ] 2.1 Port `tests/unit/test_markov_strategy.py` → `tests/unit/strategies/markov/test_persistence.py` (new imports, same scenarios)
- [ ] 2.2 Create `strategies/markov/persistence.py` — `MarkovPersistenceEngine(StrategyBase)` with exact-lift `__init__/update/evaluate/is_ready` + `parameters()` → `{"warmup_ticks", "threshold_pct"}`
- [ ] 2.3 Write VolatilityPersistence tests — 3-band classification, single price STABLE, zero range STABLE, missing data TypeError
- [ ] 2.4 Add `DirectionalPersistence` + `VolatilityPersistence` (volatility_window, _price_history, _classify_volatility) to persistence.py
- [ ] 2.5 Create `strategies/markov/__init__.py` — export all three classes
- [ ] Gate: engine tests pass, legacy `test_markov_strategy.py` still passes via old import

## Phase 3: Persistence Schema + Snapshot/Restore [PR 3]

- [ ] 3.1 Write schema tests — `init_strategy_tables` idempotent, `init_core_tables` creates `strategy_snapshots`
- [ ] 3.2 Add `init_strategy_tables(db)`, `persist_strategy_snapshot(db, ...)`, `load_latest_snapshot(db, ...)` to `core/persistence.py`
- [ ] 3.3 Write snapshot/restore tests — persist→restore identical, empty→RuntimeError, corrupt JSON→ValueError, append-only invariant
- [ ] 3.4 Add `snapshot(domain, db)`, `restore(domain, name, db)` classmethod to MarkovPersistenceEngine
- [ ] Gate: persistence tests pass, mypy/ruff clean

## Phase 4: Backward-Compat Migration [PR 3]

- [ ] 4.1 Write compat tests — `from trady_ai.core import MarkovStrategy`, engine accepts `StrategyBase` as `SignalStrategy`
- [ ] 4.2 Replace `core/markov_strategy.py` with re-export stub
- [ ] 4.3 Update `core/__init__.py` with MarkovStrategy re-export
- [ ] 4.4 Write integration test — `engine.run()` via `registry.get("PM-5M", "markov_persistence")` matches direct arg identically
- [ ] Gate: `pytest` — all tests pass, coverage ≥90% new code, `mypy src/` strict 0 errors, `ruff` clean
