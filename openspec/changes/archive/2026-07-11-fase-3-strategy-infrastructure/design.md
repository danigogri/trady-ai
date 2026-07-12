# Design: Fase 3 — Strategy Infrastructure (Markov Persistence Engine)

## Technical Approach

Migrate `MarkovStrategy` from `core/` into `strategies/markov/persistence.py` as `MarkovPersistenceEngine` with SQLite-persisted 3×3 transition matrices. Introduce `StrategyBase` (refines `SignalStrategy`), `StrategyRegistry` (dict + factory), and two V1 Markov variants (`DirectionalPersistence`, `VolatilityPersistence`). All 199 existing tests pass via backward-compat re-export stub in `core/markov_strategy.py`.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Inheritance | `StrategyBase(SignalStrategy, ABC)` | Separate hierarchy | Engine depends on `SignalStrategy` — must be IS-A |
| Registry | Dict[domain, dict[name, instance]], factory on register | Metaclass, IOC container | Simple, avoids over-engineering (per proposal risk) |
| Variants | Independent subclasses of `MarkovPersistenceEngine` | Single class with mode param | Different state spaces (UP/DOWN vs HIGH/LOW), different output semantics |
| Snapshot storage | Full 3×3 matrix JSON, append-only | Delta from previous | Simplifies restore, no state reconstruction needed |
| Domain assignment | Post-creation via `instance.domain = val` (set by registry) | Constructor param | Preserves backward-compat constructor signature |

## Module Structure

```
src/trady_ai/strategies/
├── __init__.py                   Export: StrategyBase, StrategyRegistry
├── base.py                       StrategyBase ABC
├── registry.py                   StrategyRegistry
└── markov/
    ├── __init__.py               Export: MarkovPersistenceEngine
    └── persistence.py            MarkovPersistenceEngine, DirectionalPersistence,
                                  VolatilityPersistence
core/
├── markov_strategy.py            Re-export stub (DELETED, replaced)
├── persistence.py                +init_strategy_tables(), strategy_snapshots table
└── __init__.py                   +re-export: MarkovPersistenceEngine as MarkovStrategy
```

## Data Flow

```
MarketInput → MarketStateTracker → MarketState
                                        ↓
                             StrategyRegistry.get(domain, name)
                                        ↓
                             strategy.update(state) → persists snapshot to SQLite
                             strategy.evaluate(state) → Signal
                                        ↓
                             RiskEnforcer → ExecutionDecision
```

Pipeline (9 steps) is structurally unchanged from Fase 2. The engine MAY load strategies via registry or accept them as direct args — same results either way.

## Component Design

### StrategyBase (`strategies/base.py`)

Refines `SignalStrategy` with isolation contracts and lifecycle hooks:

```python
class StrategyBase(SignalStrategy, ABC):
    @property
    @abstractmethod
    def domain(self) -> str: ...
    def on_init(self) -> None: pass            # Validate params after __init__
    def on_update(self, state: MarketState) -> None: pass
    def on_evaluate(self, state: MarketState) -> None: pass
    def on_snapshot(self) -> dict[str, Any]: ...
```

Fail-fast: invalid input type → `TypeError`, uninitialized state → `RuntimeError`, corrupted params → `ValueError`. No catch-all handlers.

### StrategyRegistry (`strategies/registry.py`)

```python
class StrategyRegistry:
    _instances: dict[str, dict[str, StrategyBase]] = {}
    _factories: dict[str, dict[str, Callable[[], StrategyBase]]] = {}

    def register(self, domain: str, name: str,
                 factory: Callable[[], StrategyBase]) -> None: ...
    def get(self, domain: str, name: str) -> StrategyBase: ...   # KeyError if unknown
    def list(self, domain: str | None = None) -> list[tuple[str, str]]: ...
    def reset(self) -> None: ...
```

- Each `(domain, name)` pair yields the same instance (singleton per key)
- Factory creates the instance, registry sets `.domain` on first `get()`
- Cross-domain instances are independent

### MarkovPersistenceEngine (`strategies/markov/persistence.py`)

The central class — replaces `MarkovStrategy` identically:

- **Constructor**: `(warmup_ticks=50, threshold_pct=0.001)` — **exact match** with legacy
- **State**: `_transition_counts` (3×3 int64), `_state_counts` (3), `_total_obs`, `_last_state`
- **update(state)**: Classifies market state via `STATE_INDEX`, increments counters, persists snapshot
- **evaluate(state)**: `argmax` on current row → maps to direction via `DIRECTION_MAP`. Zero-transition row → NEUTRAL/0.0
- **snapshot(domain, db)**: Persists current counts to `strategy_snapshots`
- **restore(domain, name, db)** (classmethod): Loads latest snapshot, reconstructs engine
- **is_ready()**: `_total_obs >= warmup_ticks`

```python
class MarkovPersistenceEngine(StrategyBase):
    def __init__(self, warmup_ticks: int = 50, threshold_pct: float = 0.001):
        self._transition_counts = np.zeros((3, 3), dtype=np.int64)
        self._state_counts = np.zeros(3, dtype=np.int64)
        self._total_obs = 0
        self._last_state: str | None = None
        self._warmup_ticks = warmup_ticks
        self._threshold_pct = threshold_pct

    @property
    def name(self) -> str: return "markov_persistence"
    @property
    def domain(self) -> str: return ""

    def update(self, state: MarketState) -> None: ...
    def evaluate(self, state: MarketState) -> Signal: ...
    def is_ready(self) -> bool: ...
    def snapshot(self, domain: str, db: sqlite_utils.Database) -> None: ...
    @classmethod
    def restore(cls, domain: str, name: str,
                db: sqlite_utils.Database) -> MarkovPersistenceEngine: ...

class DirectionalPersistence(MarkovPersistenceEngine):
    """Same state space (UP/DOWN/NEUTRAL). Maps to LONG/SHORT/NEUTRAL. Alias only."""
    pass

class VolatilityPersistence(MarkovPersistenceEngine):
    """Volatility variant: classifies HIGH/LOW/STABLE from price range."""
    def __init__(self, warmup_ticks: int = 50, threshold_pct: float = 0.001,
                 volatility_window: int = 20):
        super().__init__(warmup_ticks, threshold_pct)
        self._volatility_window = volatility_window
        self._price_history: list[Decimal] = []
        self._state_index = {"HIGH": 0, "LOW": 1, "STABLE": 2}
```

### DirectionalPersistence logic

Same as `MarkovPersistenceEngine` — state classification comes from `MarketState.state` (UP/DOWN/NEUTRAL from `MarketStateTracker`). This class exists for semantic clarity only; it's functionally identical to the base class.

### VolatilityPersistence logic

Receives `MarketState` (R3 compliance) but classifies volatility internally:

1. Append `state.price` to `_price_history` (bounded to `volatility_window`)
2. Compute `range_pct = (max - min) / min` over the window
3. Classify: `range_pct > threshold_pct` → HIGH; `< threshold_pct * 0.5` → LOW; else STABLE
4. Feed classified state through the 3×3 Markov matrix
5. Output: confidence adjustment factor (not direction), metadata includes volatility metrics

Edge cases: single price → STABLE; zero range → STABLE; missing data → TypeError.

## Persistence Schema

```sql
CREATE TABLE IF NOT EXISTS strategy_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    tick_number INTEGER NOT NULL,
    transition_counts TEXT NOT NULL,   -- JSON: [[a,b,c],[d,e,f],[g,h,i]]
    state_counts TEXT NOT NULL,        -- JSON: [x,y,z]
    warmup_ticks INTEGER NOT NULL,
    threshold_pct TEXT NOT NULL,       -- Decimal string
    snapshot_at TEXT NOT NULL,         -- ISO timestamp
    UNIQUE(strategy_name, domain, tick_number)
);
```

Added to `init_core_tables()` via `init_strategy_tables(db)`. Called from `persist_strategy_snapshot()`.

## Migration Plan

| Step | Action |
|------|--------|
| 1 | Create `strategies/base.py` — `StrategyBase` |
| 2 | Create `strategies/registry.py` — `StrategyRegistry` |
| 3 | Create `strategies/markov/persistence.py` — `MarkovPersistenceEngine` + variants |
| 4 | Add `init_strategy_tables()` + `persist_strategy_snapshot()` to `core/persistence.py` |
| 5 | Replace `core/markov_strategy.py` with re-export stub |
| 6 | Update `core/__init__.py` with re-export |
| 7 | Update `strategies/__init__.py` to export new symbols |

### Backward-Compat Re-export

```python
# core/markov_strategy.py (entire file)
from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine as MarkovStrategy

# core/__init__.py (add)
from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine as MarkovStrategy
```

All existing tests import from `core.markov_strategy` or `core` — both paths resolve.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | StrategyBase ABC | Cannot instantiate, abstract methods enforced |
| Unit | StrategyRegistry | register/get, singleton per key, KeyError, reset |
| Unit | MarkovPersistenceEngine | Port existing 164-line test — identical results vs legacy |
| Unit | VolatilityPersistence | State classification (3 bands), edge cases (single price, zero range) |
| Unit | snapshot/restore | Persist → restore → identical outputs; corrupt JSON → ValueError |
| Unit | Append-only invariant | Row count grows monotonically per (name, domain, tick) |
| Integration | Engine via registry | `engine.run()` with registry.get() matches direct strategy arg |
| Existing | 199 tests | All pass unchanged via re-export |

Coverage: ≥90% new code, mypy strict 0 errors, ruff clean.

## Risk Resolution

### R1: VolatilityPersistence threshold definition
- **Formula**: `range_pct = (max(prices) - min(prices)) / min(prices)` over `volatility_window` ticks. `> threshold_pct` → HIGH; `< threshold_pct * 0.5` → LOW; else STABLE.
- **Location**: Constructor params on `VolatilityPersistence` (defaults: `window=20`, `threshold=0.001`).
- **Edge cases**: Single price point → STABLE; zero range → STABLE; missing data → TypeError from MarketState validation.

### R2: strategy_snapshots table growth
- **Policy**: No automatic pruning for V1. Append-only preserves full replay and audit capability.
- **Estimate**: ~1KB/snapshot × 5000 ticks/market/day × 3 markets ≈ 15MB/day. Acceptable for SQLite V1.
- **Format**: Full 3×3 matrix JSON per row (not delta). Simplifies restore and point-in-time audit.
- **Documentation**: Table is unbounded. Future fases may add configurable retention policy.

### R3: Backward-compat constructor signature
- **Legacy**: `MarkovStrategy(warmup_ticks: int = 50, threshold_pct: float = 0.001)` — **preserved identically**.
- **New params**: None added to `__init__()`. `domain` set by registry post-creation (property setter).
- **Re-export**: `core/markov_strategy.py` = one-line re-import. Both `from trady_ai.core.markov_strategy import MarkovStrategy` and `from trady_ai.core import MarkovStrategy` resolve.
- **Semantics**: `warmup_ticks`/`is_ready()` code is identical. Zero behavioral drift.

## Interface Contracts

```python
# StrategyRegistry
def register(self, domain: str, name: str, factory: Callable[[], StrategyBase]) -> None
def get(self, domain: str, name: str) -> StrategyBase           # raises KeyError
def list(self, domain: str | None = None) -> list[tuple[str, str]]
def reset(self) -> None

# MarkovPersistenceEngine
def __init__(self, warmup_ticks: int = 50, threshold_pct: float = 0.001) -> None
@property def name(self) -> str                          # → "markov_persistence"
@property def domain(self) -> str                          # set by registry
def update(self, state: MarketState) -> None
def evaluate(self, state: MarketState) -> Signal
def is_ready(self) -> bool
def parameters(self) -> dict[str, Any]                   # {"warmup_ticks": ..., "threshold_pct": ...}
def snapshot(self, domain: str, db: sqlite_utils.Database) -> None
@classmethod def restore(cls, domain: str, name: str, db: sqlite_utils.Database) -> Self

# VolatilityPersistence
def __init__(self, warmup_ticks: int = 50, threshold_pct: float = 0.001,
             volatility_window: int = 20) -> None

# Persistence
def init_strategy_tables(db: sqlite_utils.Database) -> None
def persist_strategy_snapshot(db: sqlite_utils.Database, domain: str, name: str,
                              tick_number: int, counts: dict, meta: dict) -> None
def load_latest_snapshot(db: sqlite_utils.Database, domain: str,
                         name: str) -> dict[str, Any] | None
```

## Open Questions

- None blocking. `volatility_window` default (20 vs `warmup_ticks`) is a tuning choice, not a design constraint — `VolatilityPersistence.__init__` accepts it as a parameter.
