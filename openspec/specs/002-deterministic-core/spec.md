# Delta for 002-deterministic-core

**Change**: fase-3-strategy-infrastructure
**Type**: MODIFIED — refines SignalStrategy ABC, engine loads via registry, backward-compat migration

---

## MODIFIED Requirements

### Requirement: SignalStrategy ABC Location

The `SignalStrategy` abstract base class SHALL remain in `core/signal_strategy.py` as the core-owned contract. The `strategies/base.py` module SHALL provide `StrategyBase` that refines `SignalStrategy` with isolation, domain scoping, and lifecycle hooks.

The engine (`core/engine.py`) SHALL accept `SignalStrategy` (the core contract) — NOT `StrategyBase` directly. This preserves the core's dependency on the abstraction, not the concrete infrastructure.

`core/__init__.py` SHALL continue to export `SignalStrategy`. The backward-compat re-export for `MarkovStrategy` SHALL live in the stub `core/markov_strategy.py`:

```python
# core/markov_strategy.py — backward-compat re-export stub
from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine as MarkovStrategy
```

**Rationale**: Re-exporting `MarkovStrategy` in `core/__init__.py` creates a circular import: `strategies/__init__.py` → `base.py` → `core/__init__.py` → `strategies/markov/persistence.py` → `base.py`. The stub bypasses `core/__init__.py` completely, preserving backward-compat without the cycle.

(Previously: `MarkovStrategy` defined in `core/markov_strategy.py`. Now migrated to `strategies/markov/persistence.py` with stub re-export.)

#### Scenario: Backward-compat import via stub works

- GIVEN existing test code: `from trady_ai.core.markov_strategy import MarkovStrategy`
- WHEN the import is resolved
- THEN it returns the `MarkovPersistenceEngine` class from `strategies/markov/persistence.py` via the stub
- AND all 199 existing tests pass unchanged

#### Scenario: direct strategies import works without circular dependency

- GIVEN Python import: `from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine`
- WHEN the import is resolved
- THEN it succeeds without ImportError
- AND the class is usable

#### Scenario: Engine accepts StrategyBase via SignalStrategy contract

- GIVEN engine.run() signature: `run(inputs, strategy: SignalStrategy)`
- WHEN a StrategyBase subclass instance is passed
- THEN engine processes it normally (StrategyBase IS-A SignalStrategy)

---

### Requirement: Engine Pipeline Unchanged

The engine pipeline (9 steps per tick) SHALL remain structurally identical:

1. normalize → 2. state_tracker.update → 3. strategy.update → 4. strategy.evaluate → 5. risk_enforcer → 6. execute → 7. persist → 8. log → 9. loop

The engine MAY optionally load strategies via `StrategyRegistry.get(domain, name)` instead of receiving them as direct arguments. When loaded via registry, the engine receives a `SignalStrategy`-compatible instance — the pipeline is unchanged.

(Previously: Engine received strategy as direct argument only. Now: MAY also load via registry, but pipeline steps are identical.)

#### Scenario: Engine produces identical results via registry

- GIVEN engine.run(inputs, strategy=MarkovStrategy()) produces result A
- WHEN engine is configured to load ("PM-5M", "markov_persistence") from registry
- AND engine.run(inputs) produces result B
- THEN A == B (field-by-field identical ExecutionResult)

#### Scenario: warmup_ticks and is_ready() preserved

- GIVEN MarkovPersistenceEngine(warmup_ticks=50)
- WHEN fewer than 50 observations have been processed
- THEN `is_ready()` returns False
- AND `evaluate()` returns Signal(direction="NEUTRAL", confidence=0.0)

---

### Requirement: Core Persistence — Strategy Snapshots Table

`core/persistence.py` SHALL add `init_strategy_tables()` to create the `strategy_snapshots` table. Called from `init_core_tables()`.

Schema:
```sql
CREATE TABLE IF NOT EXISTS strategy_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    tick_number INTEGER NOT NULL,
    transition_counts TEXT NOT NULL,
    state_counts TEXT NOT NULL,
    warmup_ticks INTEGER NOT NULL,
    threshold_pct TEXT NOT NULL,
    snapshot_at TEXT NOT NULL,
    UNIQUE(strategy_name, domain, tick_number)
);
```

(Previously: No strategy persistence tables existed. Now: append-only snapshots for statistical traceability.)

#### Scenario: init_strategy_tables is idempotent

- GIVEN strategy_snapshots table already exists
- WHEN `init_strategy_tables(db)` is called again
- THEN no error, table unchanged (IF NOT EXISTS)

#### Scenario: init_core_tables creates strategy_snapshots

- GIVEN a fresh database with no tables
- WHEN `init_core_tables(db)` is called
- THEN strategy_snapshots table is created alongside existing 6 tables
