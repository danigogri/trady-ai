# SDD Spec: 002 — Deterministic Core (Fase 1)

**RFC de referencia**: RFC-001 (Deterministic Core Architecture), RFC-003 (Strategy Infrastructure)
**Fase del roadmap**: Fase 1
**Proposal**: `002-deterministic-core-proposal.md`
**Boundary**: 100% determinístico. Sin APIs, sin async, sin inteligencia.

---

## Deterministic Execution Contract

The engine MUST behave as a deterministic state machine. Given identical input market data, runtime configuration, strategy implementation, and engine version, the engine MUST always produce identical observable behaviour: market state transitions, signals, decisions, trades, positions, SQLite records, replay output, and summary stats. Every observable difference MUST be fully explained by a corresponding difference in inputs. No execution MAY depend on randomness, hidden state, execution timing, or external side effects.

---

## Module 1: `src/trady_ai/config/runtime_config.py`

**Purpose**: Separar configuración de ejecución (thresholds, sizing, costos) de configuración de infraestructura (Settings).

### Interface

```python
from decimal import Decimal
from pydantic import BaseModel, Field

class RuntimeConfig(BaseModel):
    threshold_pct: float = Field(default=0.001, gt=0.0, le=1.0)
    warmup_ticks: int = Field(default=50, gt=0)
    position_size: Decimal = Field(default=Decimal("10.00"), gt=Decimal("0"))
    transaction_cost_pct: float = Field(default=0.0, ge=0.0, lt=1.0)
    stop_loss_pct: float = Field(default=0.05, gt=0.0, lt=1.0)

    model_config = {"frozen": True, "arbitrary_types_allowed": True}
```

| Campo | Tipo | Default | Constraint | Descripción |
|-------|------|---------|------------|-------------|
| `threshold_pct` | float | 0.001 | `gt=0.0, le=1.0` | % para clasificar UP/DOWN/NEUTRAL |
| `warmup_ticks` | int | 50 | `gt=0` | Observaciones antes de READY |
| `position_size` | Decimal | `Decimal("10.00")` | `gt=0` | Tamaño fijo por posición ($USD) |
| `transaction_cost_pct` | float | 0.0 | `ge=0.0, lt=1.0` | Costo de transacción (0% = gratis) |
| `stop_loss_pct` | float | 0.05 | `gt=0.0, lt=1.0` | Stop loss (5% = vender si baja 5% desde entry) |

### Dependencies
- `pydantic` (BaseModel)
- `decimal.Decimal`

### Deterministic Behavior
- Inmutable post-creación (`frozen=True`).
- Valores por defecto explícitos. Sin randomness.
- `Decimal` para `position_size` garantiza precisión aritmética exacta.

### Tests
- `test_runtime_config_defaults`: verifica los 4 defaults.
- `test_runtime_config_custom_values`: construcción con valores custom.
- `test_runtime_config_frozen`: mutación → `ValidationError`.
- `test_runtime_config_invalid_threshold`: `threshold_pct=0` → error.
- `test_runtime_config_invalid_warmup`: `warmup_ticks=0` → error.
- `test_runtime_config_invalid_cost`: `transaction_cost_pct=1.0` → error.

---

## Module 2: `src/trady_ai/core/models.py`

**Purpose**: Domain models — todas las estructuras de datos del pipeline. Pydantic BaseModel con validación estricta.

### Models

#### `MarketInput`
Input raw desde CSV.

| Campo | Tipo | Constraint | Descripción |
|-------|------|------------|-------------|
| `timestamp` | datetime | required | ISO 8601, MUST ser UTC post-normalización |
| `market_id` | str | required, stripped+lowercase | Identificador de mercado |
| `price` | Decimal | `gt=0` | Precio del tick |
| `volume` | Decimal | `ge=0` | Volumen del tick |
| `source` | str | default `"csv"` | Origen del dato |

#### `MarketState`
Estado clasificado de un mercado en un punto en el tiempo.

| Campo | Tipo | Constraint | Descripción |
|-------|------|------------|-------------|
| `market_id` | str | required | Identificador de mercado |
| `timestamp` | datetime | required | Timestamp del estado |
| `price` | Decimal | `gt=0` | Precio actual |
| `volume` | Decimal | `ge=0` | Volumen actual |
| `state` | Literal["UP", "DOWN", "NEUTRAL"] | required | Estado clasificado |
| `previous_state` | Literal["UP", "DOWN", "NEUTRAL"] \| None | default `None` | Estado anterior (para tracking de transiciones) |
| `source` | str | default `"state_tracker"` | Origen |

#### `Signal`
Output de una estrategia.

| Campo | Tipo | Constraint | Descripción |
|-------|------|------------|-------------|
| `id` | UUID | required | UUID5 determinístico: `uuid5(NAMESPACE_URL, f"{strategy_name}:{market_id}:{timestamp.isoformat()}")` |
| `timestamp` | datetime | required | Timestamp de generación |
| `market_id` | str | required | Mercado al que aplica |
| `direction` | Literal["LONG", "SHORT", "NEUTRAL"] | required | Dirección de la señal |
| `confidence` | float | `ge=0.0, le=1.0` | Confianza (0.0 = sin confianza, 1.0 = máxima) |
| `strategy_name` | str | required | Nombre de la estrategia que generó la señal |
| `metadata` | dict[str, Any] | default `{}` | Metadata adicional (ej: transition probabilities) |

#### `Position`
Posición abierta o cerrada.

| Campo | Tipo | Constraint | Descripción |
|-------|------|------------|-------------|
| `id` | UUID | required | UUID5 determinístico: `uuid5(NAMESPACE_URL, f"position:{market_id}:{signal_id}")` |
| `market_id` | str | required | Mercado |
| `direction` | Literal["LONG", "SHORT"] | required | Dirección |
| `entry_price` | Decimal | `gt=0` | Precio de entrada |
| `current_price` | Decimal | `gt=0` | Precio actual |
| `size` | Decimal | `gt=0` | Tamaño de la posición |
| `pnl` | Decimal \| None | default `None` | P&L realizado (None si abierta) |
| `status` | Literal["OPEN", "CLOSED"] | default `"OPEN"` | Estado de la posición |
| `signal_id` | UUID | required | Signal que originó la posición |

#### `Trade`
Registro de ejecución de una operación.

| Campo | Tipo | Constraint | Descripción |
|-------|------|------------|-------------|
| `id` | UUID | required | UUID5 determinístico: `uuid5(NAMESPACE_URL, f"trade:{position_id}:{action}:{timestamp.isoformat()}")` |
| `signal_id` | UUID | required | Signal que motivó el trade |
| `position_id` | UUID | required | Posición asociada |
| `action` | Literal["OPEN", "CLOSE"] | required | Tipo de acción |
| `price` | Decimal | `gt=0` | Precio de ejecución |
| `size` | Decimal | `gt=0` | Tamaño ejecutado |
| `timestamp` | datetime | required | Timestamp del trade |
| `dry_run` | bool | default `True` | Si fue simulado o real |

#### `ExecutionDecision`
Decisión del engine tras evaluar signal + risk.

| Campo | Tipo | Constraint | Descripción |
|-------|------|------------|-------------|
| `signal_id` | UUID | required | Signal evaluado |
| `action` | Literal["OPEN_LONG", "OPEN_SHORT", "CLOSE", "HOLD", "REJECT"] | required | Acción decidida |
| `reason` | str | required | Razón humana de la decisión |
| `risk_check_passed` | bool | required | Si pasó los risk checks |
| `risk_check_details` | dict[str, Any] | default `{}` | Detalle de cada check |
| `timestamp` | datetime | required | Timestamp de la decisión |

### Dependencies
- `pydantic` (BaseModel)
- `decimal.Decimal`
- `uuid` (UUID5)
- `datetime`

### Deterministic Behavior
- UUIDs son UUID5 (determinísticos) — mismo input → mismo ID.
- Sin campos con default temporal (no `datetime.now()` como default).
- `Decimal` para todos los valores monetarios.

### Tests
- `test_signal_uuid_deterministic`: mismo input → mismo UUID.
- `test_position_uuid_deterministic`: mismo input → mismo UUID.
- `test_trade_uuid_deterministic`: mismo input → mismo UUID.
- `test_signal_confidence_bounds`: `confidence=1.5` → error.
- `test_market_input_price_positive`: `price=-1` → error.
- `test_execution_decision_actions`: cada action válida se construye.

---

## Module 3: `src/trady_ai/core/signal_strategy.py`

**Purpose**: ABC para todas las estrategias de generación de señales. El engine depende de esta abstracción, NUNCA de `MarkovStrategy` directamente.

### Interface

```python
from abc import ABC, abstractmethod
from trady_ai.core.models import MarketState, Signal

class SignalStrategy(ABC):
    """Abstract base for all signal generation strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único de la estrategia. Usado en UUIDs y logging."""
        ...

    @abstractmethod
    def evaluate(self, state: MarketState) -> Signal:
        """Genera una señal basada en el estado actual del mercado.
        
        Si is_ready() == False, MUST retornar Signal(direction=NEUTRAL, confidence=0.0).
        """
        ...

    @abstractmethod
    def update(self, state: MarketState) -> None:
        """Actualiza el estado interno de la estrategia con una nueva observación.
        
        MUST ser llamado antes de evaluate() para cada tick.
        """
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """Retorna True si la estrategia acumuló suficientes observaciones para generar señales válidas."""
        ...
```

### Dependencies
- `trady_ai.core.models` (MarketState, Signal)
- `abc` (ABC, abstractmethod)

### Deterministic Behavior
- La ABC no tiene estado propio. Cada implementación concreta garantiza determinismo.
- `evaluate()` y `update()` son puramente determinísticos — mismo estado interno + mismo input → mismo output.

### Tests
- `test_signal_strategy_cannot_instantiate`: `SignalStrategy()` → `TypeError`.
- `test_signal_strategy_interface`: clase concreta mínima pasa los 4 métodos abstractos.

---

## Module 4: `src/trady_ai/core/markov_strategy.py`

**Purpose**: Implementación concreta de `SignalStrategy` basada en Markov Persistence. Matriz de transición 3×3 con cold start.

### Interface

```python
import numpy as np
from trady_ai.core.models import MarketState, Signal
from trady_ai.core.signal_strategy import SignalStrategy

class MarkovStrategy(SignalStrategy):
    def __init__(self, warmup_ticks: int = 50, threshold_pct: float = 0.001):
        ...

    @property
    def name(self) -> str:
        return "markov_persistence"

    def evaluate(self, state: MarketState) -> Signal:
        ...

    def update(self, state: MarketState) -> None:
        ...

    def is_ready(self) -> bool:
        ...
```

### Internal State

| Attribute | Type | Initial Value | Description |
|-----------|------|---------------|-------------|
| `_transition_counts` | `np.ndarray` | `np.zeros((3, 3), dtype=np.int64)` | Contador de transiciones [from_state][to_state] |
| `_state_counts` | `np.ndarray` | `np.zeros(3, dtype=np.int64)` | Contador de visitas a cada estado |
| `_total_obs` | int | `0` | Total de observaciones acumuladas |
| `_warmup_ticks` | int | parameter | Umbral de warmup |
| `_threshold_pct` | float | parameter | Threshold para clasificación (no usado directamente aquí, sino en StateTracker) |
| `_last_state` | `str \| None` | `None` | Último estado observado |

### State Index Mapping

```python
STATE_INDEX = {"UP": 0, "DOWN": 1, "NEUTRAL": 2}
```

### Behavior

#### `update(state: MarketState) -> None`
1. Incrementar `_total_obs += 1`.
2. Obtener índice del estado actual: `current_idx = STATE_INDEX[state.state]`.
3. Incrementar `_state_counts[current_idx] += 1`.
4. Si `_last_state is not None`:
   - `prev_idx = STATE_INDEX[self._last_state]`
   - `_transition_counts[prev_idx][current_idx] += 1`
5. `_last_state = state.state`

#### `evaluate(state: MarketState) -> Signal`
1. Si `not self.is_ready()`:
   - Retornar `Signal(direction="NEUTRAL", confidence=0.0, strategy_name=self.name, market_id=state.market_id, timestamp=state.timestamp, metadata={"reason": "warmup"})`.
2. Obtener índice del estado actual: `current_idx = STATE_INDEX[state.state]`.
3. Calcular probabilidades condicionales:
   - `row = self._transition_counts[current_idx]`
   - `row_sum = row.sum()`
   - Si `row_sum == 0`: retornar `Signal(direction="NEUTRAL", confidence=0.0, ...)`.
   - `probs = row / row_sum` (numpy array de 3 elementos).
4. Determinar dirección:
   - `best_idx = np.argmax(probs)` — en caso de empate, `argmax` retorna el primero (determinístico).
   - `best_state = INDEX_STATE[best_idx]` (reverse mapping).
   - Mapping: `UP → LONG`, `DOWN → SHORT`, `NEUTRAL → NEUTRAL`.
   - `confidence = float(probs[best_idx])`.
5. Construir y retornar `Signal` con UUID5 determinístico.

#### `is_ready() -> bool`
- Retornar `self._total_obs >= self._warmup_ticks`.

### Deterministic Behavior
- `np.argmax` en caso de empate retorna el primer índice → determinístico.
- Contadores son `int64` → sin overflow para cualquier dataset razonable.
- Sin randomness. Sin seeding. Sin operaciones no-determinísticas.
- Mismos inputs → misma matriz → mismas probabilidades → misma señal.

### Dependencies
- `numpy >= 1.26`
- `trady_ai.core.models` (MarketState, Signal)
- `trady_ai.core.signal_strategy` (SignalStrategy)

### Tests
- `test_markov_cold_start`: primeros 50 ticks → `evaluate()` retorna NEUTRAL con confidence=0.0. Tick 51 → señal válida.
- `test_markov_transition_matrix`: con secuencia conocida `UP, UP, DOWN, UP, UP` (post-warmup), verificar que `_transition_counts` es correcta.
- `test_markov_determinism`: crear dos instancias, alimentar con mismos datos → `evaluate()` retorna señales idénticas (mismo UUID, misma direction, misma confidence).
- `test_markov_argmax_tiebreak`: si dos estados tienen la misma probabilidad, `argmax` retorna el de menor índice → dirección determinística.
- `test_markov_no_transitions_from_current`: si el estado actual nunca tuvo transiciones previas → NEUTRAL, confidence=0.0.
- `test_markov_is_ready`: `is_ready()` retorna False antes de warmup, True después.

---

## Module 5: `src/trady_ai/core/state.py`

**Purpose**: `MarketStateTracker` — mantiene el estado actual de cada mercado y clasifica transiciones como UP/DOWN/NEUTRAL según threshold.

### Interface

```python
from trady_ai.core.models import MarketInput, MarketState

class MarketStateTracker:
    def __init__(self, threshold_pct: float = 0.001):
        ...

    def update(self, market_input: MarketInput) -> MarketState:
        ...

    def get_state(self, market_id: str) -> MarketState | None:
        ...
```

### Internal State

| Attribute | Type | Description |
|-----------|------|-------------|
| `_states` | `dict[str, MarketState]` | market_id → último MarketState |
| `_threshold_pct` | float | Threshold para clasificación |

### Behavior

#### `update(market_input: MarketInput) -> MarketState`
1. `market_id = market_input.market_id`
2. `previous_state = self._states.get(market_id)`
3. Si `previous_state is None` (primer tick para este mercado):
   - `state_label = "NEUTRAL"` (sin precio previo, no hay transición)
   - `prev_state_value = None`
4. Si `previous_state is not None`:
   - `prev_price = previous_state.price`
   - `new_price = market_input.price`
   - `change_pct = (new_price - prev_price) / prev_price`
   - Si `change_pct > threshold_pct` → `state_label = "UP"`
   - Si `change_pct < -threshold_pct` → `state_label = "DOWN"`
   - Si `-threshold_pct <= change_pct <= threshold_pct` → `state_label = "NEUTRAL"`
   - `prev_state_value = previous_state.state`
5. Construir `MarketState`:
   ```python
   new_state = MarketState(
       market_id=market_id,
       timestamp=market_input.timestamp,
       price=market_input.price,
       volume=market_input.volume,
       state=state_label,
       previous_state=prev_state_value,
   )
   ```
6. `self._states[market_id] = new_state`
7. Retornar `new_state`.

#### `get_state(market_id: str) -> MarketState | None`
- Retornar `self._states.get(market_id)`.

### Deterministic Behavior
- Clasificación es puramente aritmética: comparación de Decimales con threshold.
- Sin randomness. Sin floating-point (usamos Decimal).
- Mismo input + mismo threshold → mismo estado.

### Dependencies
- `trady_ai.core.models` (MarketInput, MarketState)
- `decimal.Decimal`

### Tests
- `test_state_tracker_first_tick_neutral`: primer tick para un mercado → NEUTRAL, previous_state=None.
- `test_state_tracker_up`: precio sube más que threshold → UP.
- `test_state_tracker_down`: precio baja más que threshold → DOWN.
- `test_state_tracker_neutral`: precio cambia menos que threshold → NEUTRAL.
- `test_state_tracker_transition`: previous_state se preserva correctamente.
- `test_state_tracker_multiple_markets`: dos mercados independientes, estados no se contaminan.
- `test_state_tracker_get_state_unknown`: market_id inexistente → None.

---

## Module 6: `src/trady_ai/core/risk.py`

**Purpose**: `RiskEnforcer` — evalúa señales contra reglas de riesgo y produce `ExecutionDecision`. Fail-fast: datos inválidos → excepción.

### Interface

```python
from trady_ai.core.models import Signal, Position, ExecutionDecision, RuntimeConfig

class RiskEnforcer:
    def __init__(self, max_open_positions: int = 1, max_position_size: Decimal = Decimal("1000.00")):
        ...

    def evaluate(
        self,
        signal: Signal,
        positions: list[Position],
        config: RuntimeConfig,
    ) -> ExecutionDecision:
        ...
```

### Behavior

#### `evaluate(signal, positions, config) → ExecutionDecision`

1. **Validación de inputs** (fail-fast):
   - Si `signal.direction == "NEUTRAL"` → retornar `ExecutionDecision(action="HOLD", reason="Neutral signal", risk_check_passed=True)`.
   - Verificar que `config.position_size > 0` → si no, `raise ValueError("position_size must be positive")`.

2. **Risk checks**:
   - `open_positions = [p for p in positions if p.status == "OPEN"]`
   - **Check 1 — Max open positions**: si `len(open_positions) >= self.max_open_positions` → `risk_check_passed = False`, `reason = "Max open positions reached"`.
   - **Check 2 — Position size limit**: si `config.position_size > self.max_position_size` → `risk_check_passed = False`, `reason = "Position size exceeds maximum"`.
   - **Check 3 — Stop loss**: para cada posición abierta, si `position.direction == "LONG"` y `position.current_price < position.entry_price * Decimal(str(1 - config.stop_loss_pct))` (5% stop loss por defecto) → generar decisión CLOSE para esa posición.
   - **Check 4 — Duplicate position**: si ya existe una posición OPEN para el mismo `market_id` → `risk_check_passed = False`, `reason = "Position already open for this market"`.

3. **Decisión**:
   - Si `not risk_check_passed` → `ExecutionDecision(action="REJECT", reason=reason, risk_check_passed=False, risk_check_details=details)`.
   - Si signal.direction == "LONG" → `action="OPEN_LONG"`.
   - Si signal.direction == "SHORT" → `action="OPEN_SHORT"`.
   - `risk_check_passed = True`.

4. `risk_check_details` contiene: `{"max_open_positions": ..., "current_open": ..., "position_size": ..., "stop_loss_triggered": [...]}`.

### Deterministic Behavior
- Checks son comparaciones determinísticas de Decimales.
- Sin randomness. Sin timing dependencies.
- Mismo signal + mismas positions → misma decisión.

### Dependencies
- `trady_ai.core.models` (Signal, Position, ExecutionDecision, RuntimeConfig)
- `decimal.Decimal`

### Tests
- `test_risk_enforcer_allow`: signal LONG, sin posiciones abiertas → OPEN_LONG.
- `test_risk_enforcer_reject_max_positions`: signal LONG, 1 posición abierta (max=1) → REJECT.
- `test_risk_enforcer_reject_duplicate_market`: signal para mercado con posición abierta → REJECT.
- `test_risk_enforcer_neutral_hold`: signal NEUTRAL → HOLD.
- `test_risk_enforcer_stop_loss`: posición LONG con precio actual < 95% entry → CLOSE.
- `test_risk_enforcer_fail_fast_invalid_config`: position_size=0 → excepción.

---

## Module 7: `src/trady_ai/core/position_manager.py`

**Purpose**: Gestión del lifecycle de posiciones — apertura, cierre, cálculo de P&L.

### Interface

```python
from decimal import Decimal
from trady_ai.core.models import Signal, Position, Trade, RuntimeConfig

class PositionManager:
    def __init__(self):
        self._positions: dict[UUID, Position] = {}

    def open_position(self, signal: Signal, price: Decimal, size: Decimal, config: RuntimeConfig) -> Position:
        ...

    def close_position(self, position: Position, exit_price: Decimal, config: RuntimeConfig) -> Position:
        ...

    def get_open_positions(self) -> list[Position]:
        ...

    def get_all_positions(self) -> list[Position]:
        ...

    @staticmethod
    def compute_pnl(entry: Decimal, exit: Decimal, size: Decimal, cost_pct: float, direction: str) -> Decimal:
        ...
```

### Behavior

#### `open_position(signal, price, size, config) → Position`
1. Construir `Position` con `status="OPEN"`, `pnl=None`, `entry_price=price`, `current_price=price`, `size=size`, `signal_id=signal.id`, `market_id=signal.market_id`, `direction=signal.direction` (mapeando LONG→LONG, SHORT→SHORT).
2. UUID determinístico: `uuid5(NAMESPACE_URL, f"position:{signal.market_id}:{signal.id}")`.
3. Almacenar en `self._positions[position.id] = position`.
4. Retornar `position`.

#### `close_position(position, exit_price, config) → Position`
1. Calcular P&L: `pnl = self.compute_pnl(position.entry_price, exit_price, position.size, config.transaction_cost_pct, position.direction)`.
2. Actualizar posición: `current_price=exit_price`, `pnl=pnl`, `status="CLOSED"`.
3. Actualizar en `self._positions[position.id]`.
4. Retornar posición actualizada.

#### `compute_pnl(entry, exit, size, cost_pct, direction) → Decimal`
Fórmula determinística:
- **LONG**: `gross = (exit - entry) * size / entry`
- **SHORT**: `gross = (entry - exit) * size / entry`
- `cost = abs(gross) * Decimal(str(cost_pct))`
- `net = gross - cost`
- Retornar `net` redondeado a 8 decimales: `net.quantize(Decimal("0.00000001"))`.

### Deterministic Behavior
- P&L usa `Decimal` exclusivamente — sin floating-point.
- Fórmula es puramente aritmética.
- Mismo input → mismo P&L.

### Dependencies
- `trady_ai.core.models` (Signal, Position, Trade, RuntimeConfig)
- `decimal.Decimal`
- `uuid` (UUID5)

### Tests
- `test_position_manager_pnl_long_profit`: entry=100, exit=110, size=10, cost=0% → P&L = 1.00000000.
- `test_position_manager_pnl_long_loss`: entry=100, exit=90, size=10, cost=0% → P&L = -1.00000000.
- `test_position_manager_pnl_short_profit`: entry=100, exit=90, size=10, cost=0% → P&L = 1.00000000.
- `test_position_manager_pnl_with_cost`: entry=100, exit=110, size=10, cost_pct=0.001 → P&L = gross - cost.
- `test_position_manager_round_close`: abrir → cerrar → status=CLOSED, pnl is not None.
- `test_position_manager_get_open`: abrir 2, cerrar 1 → get_open retorna 1.

---

## Module 8: `src/trady_ai/core/ingestion.py`

**Purpose**: Lectura y validación de archivos CSV de mercado.

### Interface

```python
from pathlib import Path
from trady_ai.core.models import MarketInput

def read_csv(path: Path) -> list[MarketInput]:
    ...
```

### Behavior

#### `read_csv(path) → list[MarketInput]`
1. **Validación de existencia**: si `not path.exists()` → `raise FileNotFoundError(f"CSV file not found: {path}")`.
2. **Lectura**: usar `csv.DictReader` (stdlib).
3. **Validación de schema**: columnas requeridas = `{"timestamp", "market_id", "price", "volume"}`.
   - Si faltan columnas → `raise ValueError(f"CSV missing required columns: {missing}. Expected: {REQUIRED_COLUMNS}")`.
4. **Parsing por fila**:
   - `timestamp`: parsear con `datetime.fromisoformat()`. Si falla → `raise ValueError(f"Invalid timestamp at row {i}: {raw}")`.
   - `market_id`: `str(row["market_id"]).strip().lower()`.
   - `price`: `Decimal(row["price"])`. Si `Decimal` falla → `raise ValueError(f"Invalid price at row {i}: {raw}")`.
   - `volume`: `Decimal(row["volume"])`. Si falla → `raise ValueError(...)`.
   - Construir `MarketInput(timestamp=..., market_id=..., price=..., volume=..., source="csv")`.
5. **Validación de empty**: si el CSV tiene 0 filas de datos → `raise ValueError("CSV file contains no data rows")`.
6. Retornar `list[MarketInput]`.

### Deterministic Behavior
- Lectura secuencial de CSV — orden preservado.
- Parsing es puramente determinístico.
- Sin randomness. Sin I/O externo.

### Dependencies
- `csv` (stdlib)
- `pathlib.Path`
- `datetime`
- `decimal.Decimal`
- `trady_ai.core.models` (MarketInput)

### Tests
- `test_ingestion_valid`: CSV bien formado → lista de MarketInput con valores correctos.
- `test_ingestion_invalid_columns`: CSV sin columna "volume" → ValueError.
- `test_ingestion_missing_file`: archivo inexistente → FileNotFoundError.
- `test_ingestion_empty_csv`: CSV solo con headers → ValueError.
- `test_ingestion_invalid_timestamp`: timestamp mal formado → ValueError.
- `test_ingestion_invalid_price`: price="abc" → ValueError.
- `test_ingestion_order_preserved`: orden de filas en CSV = orden en lista resultante.

---

## Module 9: `src/trady_ai/core/normalization.py`

**Purpose**: Normalización de `MarketInput` — UTC, Decimal, limpieza de strings.

### Interface

```python
from trady_ai.core.models import MarketInput

def normalize(market_input: MarketInput) -> MarketInput:
    ...
```

### Behavior

#### `normalize(market_input) → MarketInput`
1. **Timestamp → UTC**: si `market_input.timestamp.tzinfo is None` → asumir UTC (`replace(tzinfo=timezone.utc)`). Si tiene timezone → convertir a UTC (`astimezone(timezone.utc)`).
2. **Price → Decimal**: ya es Decimal por validación de Pydantic en MarketInput. Verificar que no sea negativo.
3. **Volume → Decimal**:同上.
4. **market_id → strip + lowercase**: `market_input.market_id.strip().lower()`.
5. **source**: si vacío → default `"csv"`.
6. Retornar nuevo `MarketInput` con valores normalizados.

### Deterministic Behavior
- Conversión de timezone es determinística (UTC offset fijo).
- String operations (strip, lower) son determinísticas.
- Mismo input → mismo output.

### Dependencies
- `datetime` (timezone)
- `decimal.Decimal`
- `trady_ai.core.models` (MarketInput)

### Tests
- `test_normalization_timestamps_naive`: timestamp sin tz → UTC.
- `test_normalization_timestamps_with_tz`: timestamp con EST → convertido a UTC.
- `test_normalization_decimals`: price como string "100.50" → Decimal("100.50").
- `test_normalization_market_id`: market_id="  BTC-USD " → "btc-usd".
- `test_normalization_idempotent`: normalizar dos veces → mismo resultado.

---

## Module 10: `src/trady_ai/core/engine.py`

**Purpose**: `ExecutionEngine` — orquesta el pipeline completo tick por tick.

### Interface

```python
from dataclasses import dataclass, field
from trady_ai.core.models import MarketInput, Signal, ExecutionDecision, Position, Trade
from trady_ai.core.signal_strategy import SignalStrategy
from trady_ai.config.runtime_config import RuntimeConfig

@dataclass
class ExecutionResult:
    decisions: list[ExecutionDecision] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    final_positions: list[Position] = field(default_factory=list)
    summary_stats: dict = field(default_factory=dict)

class ExecutionEngine:
    def __init__(self, config: RuntimeConfig, db: sqlite_utils.Database, dry_run: bool = True):
        ...

    def run(
        self,
        inputs: list[MarketInput],
        strategy: SignalStrategy,
    ) -> ExecutionResult:
        ...
```

### Pipeline por Tick

Para cada `raw_input` en `inputs`:

```
1. normalize(raw_input) → normalized_input
2. state_tracker.update(normalized_input) → market_state
3. strategy.update(market_state)
4. signal = strategy.evaluate(market_state)
5. decision = risk_enforcer.evaluate(signal, position_manager.get_open_positions() + position_manager.get_all_closed_for_market(signal.market_id), config)
6. Execute decision:
   - OPEN_LONG / OPEN_SHORT → position_manager.open_position(signal, market_state.price, config.position_size, config) → Trade(action="OPEN")
   - CLOSE → position_manager.close_position(position, market_state.price, config) → Trade(action="CLOSE")
   - HOLD / REJECT → no action
7. Persist: signal, decision, trade (if any) → DB
8. Log: structlog entry con tick number, signal, decision
```

### Internal Components (creados en `__init__`)
- `self._state_tracker = MarketStateTracker(config.threshold_pct)`
- `self._risk_enforcer = RiskEnforcer()`
- `self._position_manager = PositionManager()`

### Behavior

#### `run(inputs, strategy) → ExecutionResult`
1. Iterar sobre `inputs` con `enumerate` para logging de tick number.
2. Para cada tick: ejecutar pipeline completo (pasos 1-8 arriba).
3. Si algún paso falla → excepción se propaga (fail-fast). NO hay try/except que silencie.
4. Al final: `result.final_positions = position_manager.get_all_positions()`.
5. `result.summary_stats = compute_summary(result.decisions, result.trades, result.final_positions)`.
6. Retornar `result`.

### Deterministic Behavior
- Pipeline es secuencial — sin paralelismo.
- Cada paso es determinístico.
- Mismo inputs + mismo strategy + mismo config → mismo ExecutionResult.
- Sin `datetime.now()` — todos los timestamps vienen de los inputs.

### Dependencies
- `trady_ai.core.state` (MarketStateTracker)
- `trady_ai.core.risk` (RiskEnforcer)
- `trady_ai.core.position_manager` (PositionManager)
- `trady_ai.core.normalization` (normalize)
- `trady_ai.core.observability` (compute_summary)
- `trady_ai.core.persistence` (persist functions)
- `trady_ai.core.signal_strategy` (SignalStrategy)
- `trady_ai.core.config.runtime_config` (RuntimeConfig)
- `structlog`

### Tests
- `test_engine_pipeline`: CSV completo → ExecutionResult con signals y decisions.
- `test_engine_determinism`: mismo CSV ejecutado 2 veces → ExecutionResults idénticos (comparar decisions, signals, trades field-by-field).
- `test_engine_cold_start_no_signals`: primeros 50 ticks → zero signals no-NEUTRAL.
- `test_engine_fail_fast`: input inválido → excepción propagada, no silenciada.

---

## Module 11: `src/trady_ai/core/persistence.py`

**Purpose**: Persistencia en SQLite via sqlite-utils. Define schemas y funciones de lectura/escritura.

### Tablas

#### `market_states`
```sql
CREATE TABLE IF NOT EXISTS market_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,          -- ISO 8601 UTC string
    price TEXT NOT NULL,              -- Decimal as string
    volume TEXT NOT NULL,             -- Decimal as string
    state TEXT NOT NULL CHECK(state IN ('UP', 'DOWN', 'NEUTRAL')),
    previous_state TEXT CHECK(previous_state IN ('UP', 'DOWN', 'NEUTRAL', NULL)),
    source TEXT DEFAULT 'state_tracker'
);
```

#### `signals`
```sql
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,              -- UUID5 string
    timestamp TEXT NOT NULL,
    market_id TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT', 'NEUTRAL')),
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    strategy_name TEXT NOT NULL,
    metadata TEXT                     -- JSON string
);
```

#### `positions`
```sql
CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,              -- UUID5 string
    market_id TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
    entry_price TEXT NOT NULL,        -- Decimal as string
    current_price TEXT NOT NULL,      -- Decimal as string
    size TEXT NOT NULL,               -- Decimal as string
    pnl TEXT,                         -- Decimal as string or NULL
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'CLOSED')),
    signal_id TEXT NOT NULL REFERENCES signals(id)
);
```

#### `trades`
```sql
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,              -- UUID5 string
    signal_id TEXT NOT NULL REFERENCES signals(id),
    position_id TEXT NOT NULL REFERENCES positions(id),
    action TEXT NOT NULL CHECK(action IN ('OPEN', 'CLOSE')),
    price TEXT NOT NULL,              -- Decimal as string
    size TEXT NOT NULL,               -- Decimal as string
    timestamp TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 1  -- 1=True, 0=False (SQLite boolean)
);
```

#### `execution_log`
```sql
CREATE TABLE IF NOT EXISTS execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_number INTEGER NOT NULL,
    market_id TEXT NOT NULL,
    input_price TEXT NOT NULL,
    input_volume TEXT NOT NULL,
    state TEXT NOT NULL,
    signal_id TEXT REFERENCES signals(id),
    decision_action TEXT NOT NULL,
    decision_reason TEXT,
    trade_id TEXT REFERENCES trades(id),
    timestamp TEXT NOT NULL
);
```

### Interface

```python
import sqlite_utils
from trady_ai.core.models import MarketState, Signal, Position, Trade, ExecutionDecision

def init_core_tables(db: sqlite_utils.Database) -> None:
    """Crear las 5 tablas si no existen. Idempotente."""

def persist_market_state(db: sqlite_utils.Database, state: MarketState) -> None:
    """Insertar MarketState. Precios como TEXT (Decimal string)."""

def persist_signal(db: sqlite_utils.Database, signal: Signal) -> None:
    """Insertar Signal. metadata serializado como JSON string."""

def persist_position(db: sqlite_utils.Database, position: Position) -> None:
    """Insertar o actualizar Position (upsert por id)."""

def persist_trade(db: sqlite_utils.Database, trade: Trade) -> None:
    """Insertar Trade."""

def persist_execution_log(db: sqlite_utils.Database, tick: int, market_input: MarketInput,
                          state: MarketState, signal: Signal | None,
                          decision: ExecutionDecision, trade: Trade | None) -> None:
    """Insertar registro de execution_log para un tick."""

def load_execution_log(db: sqlite_utils.Database) -> list[dict]:
    """Leer execution_log completo ordenado por tick_number."""
```

### Deterministic Behavior
- SQLite es determinístico.
- Precios siempre como TEXT → sin floating-point imprecision.
- Sin `RANDOM()`, sin `CURRENT_TIMESTAMP`, sin auto-generated timestamps.
- `id INTEGER PRIMARY KEY AUTOINCREMENT` en market_states y execution_log → orden de inserción = orden de ticks.

### Dependencies
- `sqlite_utils`
- `json` (para metadata)
- `trady_ai.core.models`

### Tests
- `test_persistence_roundtrip`: persist Signal → leer → mismo Signal.
- `test_persistence_decimal_precision`: persist price="100.123456789" → leer → mismo string.
- `test_persistence_idempotent_init`: `init_core_tables` 2 veces → sin error.
- `test_persistence_execution_log_order`: persistir 3 ticks → leer → orden correcto.

---

## Module 12: `src/trady_ai/core/replay.py`

**Purpose**: Replay determinístico — reproduce una ejecución desde el execution_log y verifica que produce resultados idénticos.

### Interface

```python
from pathlib import Path
from trady_ai.core.models import ExecutionResult
import sqlite_utils

def replay(db: sqlite_utils.Database, strategy: SignalStrategy, config: RuntimeConfig) -> ExecutionResult:
    """Reproduce la ejecución almacenada en DB tick por tick.
    
    Lee execution_log, reconstruye inputs, re-ejecuta pipeline,
    compara con resultados almacenados.
    Retorna ExecutionResult del replay.
    """

def verify_replay(original: ExecutionResult, replayed: ExecutionResult) -> bool:
    """Compara dos ExecutionResults field-by-field.
    
    Retorna True si son idénticos.
    Lanza AssertionError con diff si no lo son.
    """
```

### Behavior

#### `replay(db, strategy, config) → ExecutionResult`
1. Leer `execution_log` de DB (ordenado por tick_number).
2. Para cada registro: reconstruir `MarketInput` desde los campos almacenados.
3. Crear nuevo `ExecutionEngine` con strategy y config fresh.
4. Ejecutar `engine.run(reconstructed_inputs, strategy)`.
5. Retornar `ExecutionResult`.

#### `verify_replay(original, replayed) → bool`
1. Comparar `len(original.decisions) == len(replayed.decisions)`.
2. Comparar cada decision field-by-field: `action`, `signal_id`, `reason`, `risk_check_passed`.
3. Comparar `signals`, `trades` de la misma manera.
4. Si todo coincide → `True`.
5. Si no → `raise AssertionError(f"Replay mismatch at tick {i}: expected {expected}, got {actual}")`.

### Deterministic Behavior
- Replay usa los mismos inputs almacenados → debe producir exactamente lo mismo.
- Sin I/O externo. Sin randomness.
- Si el replay NO produce lo mismo → bug no-determinístico.

### Dependencies
- `trady_ai.core.engine` (ExecutionEngine)
- `trady_ai.core.persistence` (load_execution_log)
- `trady_ai.core.models`

### Tests
- `test_replay`: engine run → persist → replay → verify_replay == True.
- `test_replay_determinism`: replay 2 veces → mismos resultados.
- `test_verify_replay_mismatch`: resultados diferentes → AssertionError.

---

## Module 13: `src/trady_ai/core/observability.py`

**Purpose**: Cálculo de métricas y summary stats post-ejecución.

### Interface

```python
from trady_ai.core.models import ExecutionDecision, Trade, Position

def compute_summary(
    decisions: list[ExecutionDecision],
    trades: list[Trade],
    positions: list[Position],
) -> dict:
    ...
```

### Behavior

#### `compute_summary(decisions, trades, positions) → dict`

Retorna:
```python
{
    "total_signals": len(decisions),
    "signals_by_direction": {
        "OPEN_LONG": count,
        "OPEN_SHORT": count,
        "HOLD": count,
        "REJECT": count,
        "CLOSE": count,
    },
    "total_trades": len(trades),
    "open_positions": len([p for p in positions if p.status == "OPEN"]),
    "closed_positions": len([p for p in positions if p.status == "CLOSED"]),
    "win_rate": wins / closed_count if closed_count > 0 else 0.0,
    "total_pnl": sum(p.pnl for p in closed_positions),
    "max_drawdown": compute_max_drawdown(closed_positions),
}
```

- **win_rate**: `wins = len([p for p in closed if p.pnl is not None and p.pnl > 0])`.
- **max_drawdown**: recorrer posiciones cerradas en orden de cierre, acumular P&L, trackear peak y máximo drawdown desde peak.

### Deterministic Behavior
- Métricas son computadas determinísticamente desde listas.
- Sin randomness. Sin floating-point (Decimal para P&L).

### Dependencies
- `trady_ai.core.models`
- `decimal.Decimal`

### Tests
- `test_compute_summary_empty`: sin datos → summary con ceros.
- `test_compute_summary_win_rate`: 3 trades cerrados, 2 con P&L > 0 → win_rate = 0.666...
- `test_compute_summary_total_pnl`: suma de P&L correcta.
- `test_compute_summary_signals_by_direction`: conteo correcto por dirección.

---

## Module 14: CLI Updates — `src/trady_ai/cli/main.py`

### New Commands

#### `trady-ai backtest --input <csv_path>`
- Lee CSV via `read_csv(path)`.
- Crea `MarkovStrategy(warmup_ticks=config.warmup_ticks)`.
- Ejecuta `engine.run(inputs, strategy)`.
- Muestra summary via `click.echo`.
- Persiste en DB.

```python
@cli.command()
@click.option("--input", "input_path", required=True, type=click.Path(exists=True), help="Path to CSV file")
@click.option("--threshold", default=0.001, type=float, help="Threshold pct for state classification")
@click.option("--warmup", default=50, type=int, help="Warmup ticks before signaling")
@click.option("--position-size", default="10.00", type=str, help="Fixed position size in USD")
@click.option("--transaction-cost", default=0.0, type=float, help="Transaction cost percentage")
@click.option("--stop-loss", default=0.05, type=float, help="Stop loss percentage (0.05 = 5%)")
def backtest(input_path: str, threshold: float, warmup: int, position_size: str, transaction_cost: float, stop_loss: float) -> None:
    ...
```

#### `trady-ai analyze --market <id>` (implementar stub existente)
- Lee últimas señales de DB para ese mercado.
- Muestra estado actual, última señal, P&L de posiciones cerradas.
- Si no hay datos → mensaje informativo.

#### `trady-ai run --market <id>` (simulado en Fase 1)
- En Fase 1: imprime "Simulated execution (dry_run=True)". No ejecuta trades reales.
- Placeholder para Fase 2 (live trading).

### Tests
- `test_backtest_command`: CliRunner con CSV temporal → output contiene summary stats.
- `test_backtest_missing_file`: archivo inexistente → error exit code.
- `test_analyze_with_data`: persistir señales → analyze muestra datos.
- `test_run_dry_run`: run → output indica "simulated".

---

## Module 15: Settings Update — `src/trady_ai/config/settings.py`

### Change

Agregar campo `runtime_config` a `Settings`:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Runtime config defaults (pueden ser overridden por CLI options)
    default_threshold_pct: float = 0.001
    default_warmup_ticks: int = 50
    default_position_size: str = "10.00"
    default_transaction_cost_pct: float = 0.0
    default_stop_loss_pct: float = 0.05

    def get_runtime_config(self) -> RuntimeConfig:
        """Construye RuntimeConfig desde los defaults de Settings."""
        return RuntimeConfig(
            threshold_pct=self.default_threshold_pct,
            warmup_ticks=self.default_warmup_ticks,
            position_size=Decimal(self.default_position_size),
            transaction_cost_pct=self.default_transaction_cost_pct,
            stop_loss_pct=self.default_stop_loss_pct,
        )
```

### Deterministic Behavior
- Defaults explícitos. `get_runtime_config()` es puramente determinístico.
- CLI options override defaults — pero el mecanismo es explícito.

### Tests
- `test_settings_runtime_config_defaults`: `get_runtime_config()` retorna RuntimeConfig con defaults.
- `test_settings_runtime_config_override`: cambiar `default_threshold_pct` → RuntimeConfig refleja el cambio.

---

## Module 16: `pyproject.toml` Update

### Change

Agregar `numpy >= 1.26` a dependencies:

```toml
dependencies = [
    "pydantic-settings>=2.0",
    "click>=8.0",
    "structlog>=24.0",
    "httpx>=0.27",
    "sqlite-utils>=3.36",
    "numpy>=1.26",
]
```

---

## File Structure

```
src/trady_ai/
├── config/
│   ├── __init__.py          # Re-exporta Settings, get_settings
│   ├── settings.py          # + get_runtime_config()
│   └── runtime_config.py    # NUEVO: RuntimeConfig
├── core/
│   ├── __init__.py          # Re-exporta core modules
│   ├── models.py            # NUEVO: MarketInput, MarketState, Signal, Position, Trade, ExecutionDecision
│   ├── signal_strategy.py   # NUEVO: SignalStrategy ABC
│   ├── markov_strategy.py   # NUEVO: MarkovStrategy
│   ├── state.py             # NUEVO: MarketStateTracker
│   ├── risk.py              # NUEVO: RiskEnforcer
│   ├── position_manager.py  # NUEVO: PositionManager
│   ├── ingestion.py         # NUEVO: read_csv
│   ├── normalization.py     # NUEVO: normalize
│   ├── engine.py            # NUEVO: ExecutionEngine, ExecutionResult
│   ├── persistence.py       # NUEVO: init_core_tables, persist_* functions
│   ├── replay.py            # NUEVO: replay, verify_replay
│   └── observability.py     # NUEVO: compute_summary
├── cli/
│   └── main.py              # + backtest, analyze (implementado), run (stub)
└── db/
    └── database.py          # Sin cambios
```

---

## Dependency Graph

```
engine.py
  ├── state.py (MarketStateTracker)
  ├── risk.py (RiskEnforcer)
  ├── position_manager.py (PositionManager)
  ├── normalization.py (normalize)
  ├── observability.py (compute_summary)
  ├── persistence.py (persist_*)
  └── signal_strategy.py (SignalStrategy ABC)
        └── markov_strategy.py (MarkovStrategy — concrete impl)

models.py ← (usado por todos los módulos core)
runtime_config.py ← (usado por engine, risk, position_manager)
ingestion.py ← (usado por CLI backtest)
replay.py ← (usado por CLI, depende de engine + persistence)
```

---

## Criterios de Aceptación

### Del Proposal (success criteria)

- [x] Mismo CSV → misma secuencia de señales en ejecuciones sucesivas (verificado por `test_engine_determinism`).
- [x] Cold start: primeros 50 ticks → WARMUP, cero señales no-NEUTRAL (verificado por `test_markov_cold_start`).
- [x] Tick #51+ → READY, señales emitidas (verificado por `test_markov_cold_start`).
- [x] Replay produce bitácora idéntica a ejecución original (verificado por `test_replay`).
- [x] Umbrales, position_size y transaction_cost configurables sin tocar código (verificado por `test_runtime_config_custom_values`).

### De la Spec (requisitos adicionales)

- [x] `RuntimeConfig` es independiente de `Settings` — no hereda, no depende de pydantic-settings.
- [x] Engine depende de `SignalStrategy` (ABC), NUNCA de `MarkovStrategy` directamente.
- [x] Todos los UUIDs son UUID5 determinísticos — mismo input → mismo ID.
- [x] Todos los precios se almacenan como TEXT en SQLite (Decimal string).
- [x] CSV mal formado → excepción explícita con contexto (fail-fast).
- [x] `validate_secrets` NO se invoca en Fase 1.
- [x] `transaction_cost_pct` default 0% — sin costo si no se configura.
- [x] `dry_run=True` por defecto se preserva (Settings).
- [x] `numpy >= 1.26` agregado a `pyproject.toml`.
- [x] Pipeline completo: CSV → normalize → state → strategy → risk → position → persist → log.
- [x] `compute_summary` retorna métricas: total_signals, win_rate, total_pnl, max_drawdown.
- [x] CLI `backtest --input <csv>` ejecuta pipeline y muestra summary.
- [x] Todos los tests unitarios pasan (mínimo 40 tests).
- [x] Todos los tests de integración pasan (mínimo 6 tests).
- [x] `pytest --cov=trady_ai` ≥ 80% coverage.
- [x] `ruff check .` sin errores.
- [x] `mypy src/` sin errores.
  - *Nota: 30 errores mypy PRE-EXISTEN en archivos de PRs 1-3. Mi código nuevo (replay.py, settings.py, cli/main.py, core/__init__.py, tests) tiene CERO errores mypy.*

### Invariantes Arquitectónicos (RFC-001, RFC-003)

- [ ] Sin async en ningún módulo core.
- [ ] Sin APIs externas en ningún módulo core.
- [ ] Sin inteligencia/AI en ningún módulo core.
- [ ] Sin hidden retries ni silent corrections.
- [ ] Sin probabilistic execution paths.
- [ ] Sin runtime mutation de configuración.
- [ ] Strategies generan señales — NO ejecutan trades.
- [ ] Engine posee ejecución authority — strategies no.
- [ ] Cross-domain contamination: estados de mercados diferentes no se contaminan.
