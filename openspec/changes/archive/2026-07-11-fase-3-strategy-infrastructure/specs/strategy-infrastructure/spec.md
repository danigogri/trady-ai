# Strategy Infrastructure Specification

**Domain**: strategy-infrastructure | **Type**: New | **RFC**: RFC-003
**Package**: `src/trady_ai/strategies/`

## Purpose

Formalize strategies as isolated first-class modules. Strategies generate signals — they do NOT own execution authority (RFC-003 Final Principle).

---

## Requirements

### R1: Strategy Base Class

`strategies/base.py` SHALL provide `StrategyBase` refining `core.signal_strategy.SignalStrategy` with:
- Frozen signal output (Signal = analytical conclusion, NOT execution command)
- Deterministic contract: same state + same internal state → same output
- Fail-fast on invalid inputs (no silent degradation)
- Isolation: no access to adapters, DB, governance, or other strategies

Interface: `name`, `domain`, `evaluate(state) -> Signal`, `update(state) -> None`, `is_ready() -> bool`, `parameters() -> dict`.

**Scenario: rejects non-MarketState input**
- GIVEN a StrategyBase subclass instance
- WHEN `evaluate()` receives a non-MarketState object
- THEN raises `TypeError` WITHOUT producing a signal

**Scenario: evaluate before ready returns warmup signal**
- GIVEN `is_ready() == False`
- WHEN `evaluate(state)` is called
- THEN returns `Signal(direction="NEUTRAL", confidence=0.0, metadata={"reason": "warmup"})`

**Scenario: no imports from adapters/persistence/governance**
- GIVEN a StrategyBase subclass module
- WHEN inspecting imports
- THEN does NOT import from `trady_ai.adapters`, `trady_ai.core.persistence`, `trady_ai.governance`

---

### R2: Strategy Registry

`strategies/registry.py` SHALL provide `StrategyRegistry` managing instances by `(domain, name)`:
- Each `(domain, name)` → isolated instance (singleton per key)
- Factory-based creation via registered factory functions
- Domain scoping: strategies belong to execution domains (e.g. "PM-5M")
- No cross-domain access between strategy instances

Interface: `register(domain, name, factory)`, `get(domain, name) -> StrategyBase`, `list(domain=None)`, `reset()`.

**Scenario: isolated instance per (domain, name)**
- GIVEN registry with factory for ("PM-5M", "markov_persistence")
- WHEN `get("PM-5M", "markov_persistence")` called twice vs `get("BINANCE-INTRADAY", "markov_persistence")`
- THEN same-domain returns SAME instance; cross-domain returns DIFFERENT instance

**Scenario: raises on unknown key**
- GIVEN no registration for ("UNKNOWN", "foo")
- WHEN `get("UNKNOWN", "foo")` called
- THEN raises `KeyError`

---

### R3: Signal as Deterministic Output

Per RFC-003 §Signal Philosophy:
- Signal fields frozen: id (UUID5), timestamp, market_id, direction, confidence, strategy_name, metadata
- Signal is NOT execution command — core engine decides execution
- Signal MUST NOT contain execution instructions or order parameters

**Scenario: signal consumed by core, not executed directly**
- GIVEN strategy produces `Signal(direction="LONG", confidence=0.75)`
- WHEN engine receives the signal
- THEN `RiskEnforcer.evaluate()` decides action (OPEN_LONG/HOLD/REJECT) — signal alone triggers nothing

---

### R4: Isolation Enforcement

Per RFC-003 §Isolation Doctrine:
- Strategy MAY NOT mutate unrelated strategies, inherit uncontrolled context, absorb adapter ownership, contaminate unrelated domains
- Every strategy independently testable, removable, replaceable, auditable, replayable

**Scenario: independently testable without engine/DB**
- GIVEN a MarkovPersistenceEngine from registry
- WHEN tested with mock MarketState inputs
- THEN produces deterministic outputs without engine, adapters, or DB

---

### R5: Fail-Fast Behavior

Per RFC-003 §Failure Philosophy — rejects silent degradation, hidden fallback, invisible recalibration:
- Invalid input type → `TypeError`
- Uninitialized state → `RuntimeError`
- Corrupted parameters → `ValueError`
- No catch-all handlers in strategy code. Engine catches at pipeline boundary only.

**Scenario: engine does not silently catch strategy exceptions**
- GIVEN strategy raises `RuntimeError` during `evaluate()`
- WHEN engine processes the tick
- THEN exception propagates — no fallback signal, no silent NEUTRAL

---

### R6: Lifecycle Hooks

Hooks: `on_init()`, `on_update(state)`, `on_evaluate(state)`, `on_snapshot()`.
MUST be deterministic. MUST NOT access external systems.

**Scenario: on_init validates parameters**
- GIVEN strategy with `warmup_ticks=-1`
- WHEN `on_init()` called
- THEN raises `ValueError("warmup_ticks must be > 0")`

---

## File Structure

```
src/trady_ai/strategies/
├── __init__.py       # Exports StrategyBase, StrategyRegistry
├── base.py           # StrategyBase ABC
├── registry.py       # StrategyRegistry
└── markov/
    ├── __init__.py
    └── persistence.py  # MarkovPersistenceEngine
```
