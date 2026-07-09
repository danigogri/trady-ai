# SDD Design: 002 — Deterministic Core

**Baseline**: Bootstrap 001 (pydantic-settings, click, structlog, sqlite-utils, src-layout, frozen Settings)
**Spec**: `002-deterministic-core-spec.md` (16 módulos, 1,158 líneas)
**Boundary**: Fase 1 — 0 APIs, 0 async, 0 AI.

---

## Engine Pipeline (9 pasos por tick)

```
  CSV ──► read_csv() ──► normalize() ──► MarketInput list
                                                          
  Por cada MarketInput:                                  
    1. normalize(input) ───► MarketInput (UTC, Decimal)  
    2. state_tracker.update() ──► MarketState             
    3. strategy.update(state) ──► internal state muta     
    4. signal = strategy.evaluate(state) ──► Signal        
    5. risk_enforcer.evaluate(signal, positions, cfg) ──► ExecutionDecision
    6. execute(decision):
       ├── OPEN_LONG/SHORT → position_manager.open() → Trade(OPEN)
       ├── CLOSE           → position_manager.close() → Trade(CLOSE)
       └── HOLD/REJECT     → no-op
    7. persist(signal, decision, trade, execution_log) → SQLite
    8. log (structlog)
    9. loop

  ──► ExecutionResult { decisions, trades, signals, final_positions, summary_stats }
```

Pipeline es **secuencial puro** — sin async, sin threads, sin batch. Cada tick es atómico: o toda la cadena se completa, o la excepción se propaga (fail-fast).

---

## Diseño por Módulo

### M1. `runtime_config.py` (config/)

Pydantic `BaseModel` frozen con 5 campos. **NO hereda de Settings** — son concerns distintos.

```python
class RuntimeConfig(BaseModel):
    threshold_pct: float       # default 0.001, (0, 1]
    warmup_ticks: int          # default 50, > 0
    position_size: Decimal     # default "10.00", > 0
    transaction_cost_pct: float  # default 0.0, [0, 1)
    stop_loss_pct: float       # default 0.05, (0, 1)
    model_config = {"frozen": True, "arbitrary_types_allowed": True}
```

**Decisiones**: `Decimal` para position_size (precisión de dinero), `float` para porcentajes (umbrales, no monetarios). Frozen ⇒ inmutabilidad post-creación.

**Edge cases**: `threshold_pct=0` → error (debe ser > 0). `transaction_cost_pct=1.0` → error (debe ser < 1).

---

### M2. `models.py` (core/)

6 modelos Pydantic: `MarketInput`, `MarketState`, `Signal`, `Position`, `Trade`, `ExecutionDecision`. Todos con **UUID5 determinísticos**:

| Modelo | UUID5 namespace | input |
|--------|-----------------|-------|
| Signal | `uuid5(NURL, f"{name}:{market}:{ts}")` | strategy_name + market_id + timestamp |
| Position | `uuid5(NURL, f"position:{market}:{signal_id}")` | market_id + signal.id |
| Trade | `uuid5(NURL, f"trade:{pos_id}:{action}:{ts}")` | position_id + action + timestamp |

**Determinismo**: `NURL = uuid.NAMESPACE_URL`. Sin `datetime.now()` como default. Timestamps vienen de inputs. `Decimal` para todo valor monetario.

**Edge cases**: `price=0` → error (`gt=0`). `confidence=1.5` → error. `direction="INVALID"` → error por Literal.

---

### M3. `signal_strategy.py` (core/)

```python
class SignalStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def evaluate(self, state: MarketState) -> Signal: ...
    @abstractmethod
    def update(self, state: MarketState) -> None: ...
    @abstractmethod
    def is_ready(self) -> bool: ...
```

**Contrato**: Engine depende de esta ABC, nunca de `MarkovStrategy` directamente. `evaluate()` + `update()` son side-effect-free desde afuera (muta estado interno pero es determinístico). Si `not is_ready()` ⇒ Signal(NEUTRAL, confidence=0.0).

---

### M4. `markov_strategy.py` (core/)

Matriz de transición 3×3 con **numpy `int64`**. Sin seeding, sin randomness.

```python
STATE_INDEX = {"UP": 0, "DOWN": 1, "NEUTRAL": 2}

# update(state):
#   self._total_obs += 1
#   idx = STATE_INDEX[state.state]
#   self._state_counts[idx] += 1
#   if self._last_state:
#       prev = STATE_INDEX[self._last_state]
#       self._transition_counts[prev][idx] += 1
#   self._last_state = state.state
#
# evaluate(state):
#   if not is_ready(): return Signal(NEUTRAL, 0.0, ...)
#   idx = STATE_INDEX[state.state]
#   row = self._transition_counts[idx]
#   if row.sum() == 0: return Signal(NEUTRAL, 0.0, ...)
#   probs = row / row.sum()              # numpy broadcasting
#   best = INDEX_STATE[np.argmax(probs)]  # argmax = deterministic on ties
#   direction = {"UP":"LONG","DOWN":"SHORT","NEUTRAL":"NEUTRAL"}[best]
#   return Signal(direction, float(probs.max()), ...)
```

| Decisión | Alternativas | Rationale |
|----------|-------------|-----------|
| **numpy** `int64` | Python list of lists | Broadcasting para probs en 1 línea, tipado fijo, sin loops |
| `np.argmax` | `max()` + `index()` | Argmax es O(n) nativo, determinístico en empates (primer índice) |
| `int64` counts | `float64` | Overflow-proof para millones de ticks |

**Edge cases**: `row.sum() == 0` (nunca viste transición desde este estado desde warmup) ⇒ NEUTRAL. Empates en `argmax` ⇒ siempre mismo índice (determinístico).

---

### M5. `state.py` (core/) — MarketStateTracker

```python
# update(input):
#   prev = self._states.get(input.market_id)
#   if not prev:  # first tick
#       state = "NEUTRAL", prev_state = None
#   else:
#       change = (input.price - prev.price) / prev.price
#       if change > threshold:  state = "UP"
#       elif change < -threshold: state = "DOWN"
#       else: state = "NEUTRAL"
#       prev_state = prev.state
#   new = MarketState(market_id, input.timestamp, input.price, input.volume, state, prev_state)
#   self._states[market_id] = new
#   return new
```

**Determinismo**: clasificación con `Decimal` + `float` threshold. `change_pct` usa Decimal arithmetic exacto para el numerador. Sin FP comparison tricks.

**Edge cases**: Primer tick para un market_id ⇒ NEUTRAL. Dos mercados independientes: `_states` es `dict[str, MarketState]` — no contaminación.

---

### M6. `risk.py` (core/) — RiskEnforcer: 5 checks

```python
# evaluate(signal, positions, config):
#   if signal.direction == "NEUTRAL": return HOLD("Neutral signal")
#   if config.position_size <= 0: raise ValueError(...)
#
#   open_positions = [p for p in positions if p.status == "OPEN"]
#   details = {}
#
#   # C1: Max open positions
#   if len(open_positions) >= self.max_open_positions:
#       return REJECT("Max open positions reached")
#
#   # C2: Position size limit
#   if config.position_size > self.max_position_size:
#       return REJECT("Position size exceeds max")
#
#   # C3: Stop loss (por cada posición abierta)
#   stop_triggered = [
#       p for p in open_positions
#       if p.direction == "LONG" and p.current_price < p.entry_price * Decimal(str(1 - config.stop_loss_pct))
#   ]
#   if stop_triggered:
#       return CLOSE(..., action="CLOSE", stop_loss_triggered=stop_triggered)
#
#   # C4: Duplicate market
#   if any(p.market_id == signal.market_id for p in open_positions):
#       return REJECT("Position already open for market")
#
#   # C5 (implicit): direction → OPEN_LONG / OPEN_SHORT
#   action = "OPEN_LONG" if signal.direction == "LONG" else "OPEN_SHORT"
#   return decision(action=action, risk_check_passed=True)
```

**Stop loss math**: `entry_price * Decimal(str(1 - stop_loss_pct))`. Ej: 100 * (1 - 0.05) = 95. Si `current_price < 95` ⇒ CLOSE. Determinístico.

**Edge cases**: stop_loss_triggered lista vacía pero hay posiciones abiertas para el mercado ⇒ REJECT por C4 antes. Signal NEUTRAL ⇒ HOLD sin fallar.

---

### M7. `position_manager.py` (core/)

**In-memory** (`_positions: dict[UUID, Position]`). No DB propia — la DB la escribe el engine vía persistence.

```python
# open_position(signal, price, size, config):
#   pos = Position(id=uuid5(NURL, f"position:{signal.market_id}:{signal.id}"),
#                  market_id=signal.market_id,
#                  direction="LONG"|"SHORT",
#                  entry_price=price, current_price=price,
#                  size=size, pnl=None, status="OPEN",
#                  signal_id=signal.id)
#   self._positions[pos.id] = pos; return pos
#
# compute_pnl(entry, exit, size, cost_pct, direction):
#   if direction == "LONG":  gross = (exit - entry) * size / entry
#   else:                    gross = (entry - exit) * size / entry
#   cost = abs(gross) * Decimal(str(cost_pct))
#   return (gross - cost).quantize(Decimal("0.00000001"))
```

**P&L fórmula**: `(exit - entry) * size / entry` — retorno simple sobre el capital invertido. Cost es porcentual sobre gross. Quantize a 8 decimales.

**Decision**: In-memory (vs solo DB) porque el engine necesita acceso O(1) por tick y la DB es el *commit* final, no el source of truth durante la ejecución.

---

### M8. `ingestion.py` (core/)

`csv.DictReader` sobre stdlib. **NO pandas** — la dependencia adicional no justifica el peso para CSVs planos.

```python
# read_csv(path):
#   if not path.exists(): raise FileNotFoundError(...)
#   with open(path) as f:
#       reader = csv.DictReader(f)
#       REQUIRED = {"timestamp", "market_id", "price", "volume"}
#       if not REQUIRED.issubset(reader.fieldnames):
#           raise ValueError(f"Missing: {REQUIRED - set(reader.fieldnames)}")
#       rows = []
#       for i, row in enumerate(reader):
#           ts = datetime.fromisoformat(row["timestamp"])
#           rows.append(MarketInput(ts, row["market_id"].strip().lower(),
#                        Decimal(row["price"]), Decimal(row["volume"]), "csv"))
#   if not rows: raise ValueError("Empty CSV")
#   return rows
```

**Edge cases**: timestamp inválido → `fromisoformat` lanza `ValueError`. Price="abc" → `Decimal` lanza. Archivo vacío (solo headers) → error explícito.

---

### M9. `normalization.py` (core/)

```python
# normalize(input):
#   ts = input.timestamp
#   if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
#   else: ts = ts.astimezone(timezone.utc)
#   mid = input.market_id.strip().lower()
#   src = input.source or "csv"
#   return MarketInput(ts, mid, input.price, input.volume, src)
```

Idempotente: normalizar dos veces produce el mismo resultado. `astimezone(utc)` es determinístico.

---

### M10. `engine.py` (core/) — ExecutionEngine

```python
# __init__(config, db, dry_run=True):
#   self._config = config
#   self._db = db
#   self._dry_run = dry_run
#   self._state_tracker = MarketStateTracker(config.threshold_pct)
#   self._risk_enforcer = RiskEnforcer()
#   self._position_manager = PositionManager()
#
# run(inputs, strategy):
#   persistence.init_core_tables(self._db)  # one-time schema setup
#   for tick_num, raw_input in enumerate(inputs, 1):
#       normalized = normalize(raw_input)
#       state = self._state_tracker.update(normalized)
#       strategy.update(state)
#       signal = strategy.evaluate(state)
#       positions = self._position_manager.get_open_positions()
#       decision = self._risk_enforcer.evaluate(signal, positions, self._config)
#
#       trade = None
#       if decision.action in ("OPEN_LONG", "OPEN_SHORT"):
#           p = self._position_manager.open_position(signal, state.price, self._config.position_size, self._config)
#           trade = Trade(signal.id, p.id, "OPEN", state.price, p.size, state.timestamp, self._dry_run)
#       elif decision.action == "CLOSE":
#           for p in positions:
#               closed = self._position_manager.close_position(p, state.price, self._config)
#               trade = Trade(signal.id, p.id, "CLOSE", state.price, closed.size, state.timestamp, self._dry_run)
#
#       persistence.persist_signal(self._db, signal)
#       persistence.persist_execution_log(self._db, tick_num, raw_input, state, signal, decision, trade)
#       if trade: persistence.persist_trade(self._db, trade)
#       log.info("tick", tick=tick_num, market=state.market_id, signal=signal.direction, decision=decision.action)
#
#   result = ExecutionResult(
#       decisions=[...], trades=[...], signals=[...],
#       final_positions=self._position_manager.get_all_positions()
#   )
#   result.summary_stats = compute_summary(result.decisions, result.trades, result.final_positions)
#   return result
```

| Decisión | Alternativas | Rationale |
|----------|-------------|-----------|
| **Sequential sync** | Async | Fase 1 no tiene I/O externo. Async agrega complejidad, no throughput |
| **try/except none** | Error recovery | Fail-fast: error en cualquier paso propaga la excepción |

---

### M11. `persistence.py` (core/)

5 tablas SQLite vía `sqlite-utils`: `market_states`, `signals`, `positions`, `trades`, `execution_log`. Decimales como TEXT.

```python
# init_core_tables(db):  CREATE TABLE IF NOT EXISTS × 5, idempotente
# persist_*(db, model):  db[table].insert(model.dict(), alter=True)
```

No se usa `sqlite_utils.upsert` para `positions` porque el ID es UUID5 determinístico y la posición se crea una sola vez.

---

### M12. `replay.py` (core/)

```python
# replay(db, strategy, config):
#   log = persistence.load_execution_log(db)  # ORDER BY tick_number
#   inputs = [reconstruct_market_input(row) for row in log]
#   engine = ExecutionEngine(config, db, dry_run=True)
#   return engine.run(inputs, strategy)
#
# verify_replay(original, replayed):
#   for i, (a, b) in enumerate(zip(original.signals, replayed.signals)):
#       assert a == b, f"Mismatch at signal {i}: {a} != {b}"
#   for i, (a, b) in enumerate(zip(original.trades, replayed.trades)):
#       assert a == b, f"Mismatch at trade {i}"
#   return True
```

**Determinismo**: reconstruye MarketInput exactos desde `execution_log` (precios como Decimal string). Engine fresh produce resultado idéntico. Si no ⇒ bug.

---

### M13. `observability.py` (core/)

```python
# compute_summary(decisions, trades, positions):
#   closed = [p for p in positions if p.status == "CLOSED"]
#   wins = sum(1 for p in closed if p.pnl and p.pnl > 0)
#   pnl_total = sum(p.pnl or 0 for p in closed)
#   return {
#       "total_signals": len(decisions),
#       "signals_by_direction": Counter(d.action for d in decisions),
#       "total_trades": len(trades),
#       "open_positions": sum(1 for p in positions if p.status == "OPEN"),
#       "closed_positions": len(closed),
#       "win_rate": wins / len(closed) if closed else 0.0,
#       "total_pnl": pnl_total,
#       "max_drawdown": compute_max_drawdown(closed),
#   }
```

**max_drawdown**: recorrer posiciones cerradas cronológicamente, trackear running P&L, calcular peak-to-trough máximo.

---

### M14. `cli/main.py` — backtest command

```python
# @cli.command()
# @click.option("--input", required=True)
# @click.option("--threshold", default=0.001)
# @click.option("--warmup", default=50)
# def backtest(input_path, threshold, warmup, position_size="10.00", transaction_cost=0.0, stop_loss=0.05):
#     settings = get_settings()
#     config = RuntimeConfig(threshold, warmup, Decimal(position_size), transaction_cost, stop_loss)
#     db = get_db(settings)
#     inputs = read_csv(Path(input_path))
#     strategy = MarkovStrategy(config.warmup_ticks, config.threshold_pct)
#     engine = ExecutionEngine(config, db, dry_run=True)
#     result = engine.run(inputs, strategy)
#     click.echo(result.summary_stats)
```

**analyze** se implementa como lectura de DB: últimas señales + P&L. **run** queda como stub ("Simulated — dry_run=True").

---

### M15. `settings.py` — 5 new defaults + `get_runtime_config()`

```python
# class Settings(BaseSettings):
#     ...
#     default_threshold_pct: float = 0.001
#     default_warmup_ticks: int = 50
#     default_position_size: str = "10.00"
#     default_transaction_cost_pct: float = 0.0
#     default_stop_loss_pct: float = 0.05
#
#     def get_runtime_config(self) -> RuntimeConfig:
#         return RuntimeConfig(
#             threshold_pct=self.default_threshold_pct,
#             warmup_ticks=self.default_warmup_ticks,
#             position_size=Decimal(self.default_position_size),
#             transaction_cost_pct=self.default_transaction_cost_pct,
#             stop_loss_pct=self.default_stop_loss_pct,
#         )
```

**Separación**: Settings = infraestructura (env, db_path, dry_run). RuntimeConfig = ejecución (thresholds, sizing). `position_size` como `str` en Settings (env vars son strings) y `Decimal` en RuntimeConfig.

---

### M16. `pyproject.toml`

Agregar `"numpy>=1.26"` a `dependencies`.

---

## Decisiones Técnicas

| Decisión | Opción | Alternativa | Rationale |
|----------|--------|-------------|-----------|
| **Matriz transición** | numpy `int64` | Python `list[list[int]]` | Broadcasting, tipado fijo, sin loops. Dependencia justificada |
| **Moneda** | `Decimal` | `float` | Errores de redondeo de float en P&L son inaceptables en finanzas |
| **UUIDs** | UUID5 | UUID4 | Mismo input ⇒ mismo ID. Replay y verificación posible |
| **Pipeline** | Secuencial sync | Async | Sin I/O externo en Fase 1. Async = complejismo innecesario |
| **PositionManager** | In-memory dict | Solo DB writes | O(1) lookups por tick. DB es commit, no source of truth durante runtime |
| **RuntimeConfig** | Pydantic frozen, separado | Dentro de Settings | Concerns distintos. Settings = infraestructura, RuntimeConfig = ejecución |
| **CSV parsing** | `csv.DictReader` | pandas | Dependencia adicional de 30MB+ para leer CSVs planos |
| **Floating point en %** | `float` | `Decimal` | Thresholds y costos son razonables con float. `transaction_cost_pct=0.0` es exacto |

---

## Testing Strategy

| Capa | Cantidad | Coverage targets |
|------|----------|-----------------|
| Unit (models, config, state, risk, markov) | 32+ tests | Cada módulo: defaults, validación, edge cases, determinismo |
| Integration (persistence roundtrip, engine pipeline) | 10+ tests | CSV → DB → replay → verify |
| E2E (CLI backtest) | 4 tests | CliRunner con CSV temporal |

**Determinism test pattern**: ejecutar engine.run() dos veces con mismos inputs ⇒ `assert result1 == result2` field-by-field.

---

## Riesgos Técnicos

| Riesgo | Mitigación |
|--------|-----------|
| `np.argmax` cambia comportamiento en numpy >2.x | Pin numpy>=1.26,<3. En caso de empate, `argmax` está documentado como first-occurrence |
| `Decimal.quantize` con cost_pct puede causar `Inexact` | Usar `quantize(..., rounding=ROUND_HALF_EVEN)` explícito |
| SQLite `execution_log` con millones de filas | Fase 1 es local-first, CSVs acotados. Indexar por tick_number |
| `fromisoformat` en Python <3.11 no parsea todos los ISO 8601 | Python 3.12 requerido. `fromisoformat` es completo desde 3.11 |

---

## Open Questions

- [ ] Separación trades versus execution_log: ¿Tiene sentido tener ambas tablas? Trade es el registro contable, execution_log es el audit trail completo. Confirmar que no duplican información.
- [ ] `stop_loss_pct` aplica por posición individual. ¿Debería haber un stop loss global (portfolio drawdown)?
