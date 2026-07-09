# Tasks: Deterministic Core (Fase 1)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,870 (14 new + 3 modified + ~54 tests) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Foundation → PR 2: Strategy+State → PR 3: Pipeline+Engine → PR 4: Assembly+Verify |
| Delivery strategy | ask-always |
| Chain strategy | stacked-to-main |

```
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | PR | Notes |
|------|------|-----|-------|
| 1 | Foundation: pyproject, models, runtime_config, signal_strategy ABC | PR 1 → main | ~380 lines; base de todas las dependencias |
| 2 | Strategy+State: markov, state tracker, normalization, ingestion | PR 2 → main | ~450 lines; independiente de pipeline, depende de PR 1 |
| 3 | Pipeline+Engine: risk, position_manager, engine, persistence, observability | PR 3 → main | ~500 lines; core del execution engine |
| 4 | Assembly+Verify: replay, CLI, settings, E2E tests, verification | PR 4 → main | ~540 lines; wrap final + tests de integración |

---

## Phase 1: Foundation (5 tareas)

### [x] Tarea 1.1: Agregar `numpy >= 1.26` a pyproject.toml

**Archivos**: `pyproject.toml` | **Dep**: —
**Qué**: Agregar `"numpy>=1.26"` a `dependencies` en pyproject.toml.
**CA**: `pip install -e "."` no falla; `import numpy` desde el venv funciona.
**Tests**: Ninguno (verificación manual con pip install).

### [x] Tarea 1.2: Crear `RuntimeConfig` en `config/runtime_config.py`

**Archivos**: `src/trady_ai/config/runtime_config.py`, `src/trady_ai/config/__init__.py` (re-export) | **Dep**: —
**Qué**: Clase `RuntimeConfig(BaseModel)` frozen con 5 campos: `threshold_pct` (0.001), `warmup_ticks` (50), `position_size` (Decimal("10.00")), `transaction_cost_pct` (0.0), `stop_loss_pct` (0.05). Validaciones Pydantic `gt`/`ge`/`lt`/`le`.
**CA**: `RuntimeConfig()` crea con defaults; `RuntimeConfig(threshold_pct=0)` → `ValidationError`; frozen impide mutación.
**Tests**: `test_runtime_config_defaults`, `test_runtime_config_custom_values`, `test_runtime_config_frozen`, `test_runtime_config_invalid_threshold`, `test_runtime_config_invalid_warmup`, `test_runtime_config_invalid_cost`.

### [x] Tarea 1.3: Crear modelos de dominio en `core/models.py`

**Archivos**: `src/trady_ai/core/models.py`, `src/trady_ai/core/__init__.py` (re-export) | **Dep**: 1.2
**Qué**: 6 clases Pydantic: `MarketInput`, `MarketState`, `Signal` (UUID5), `Position` (UUID5), `Trade` (UUID5), `ExecutionDecision`. Todos con campos tipados, validaciones (`gt=0`, `ge=0`, `le=1.0`), UUIDs determinísticos via `uuid5(NAMESPACE_URL, ...)`. Sin `datetime.now()` como default.
**CA**: Seis modelos compilan sin errores mypy; `Signal(id=uuid5(...))` mismo input → mismo UUID; `MarketInput(price=-1)` → `ValidationError`.
**Tests**: `test_signal_uuid_deterministic`, `test_position_uuid_deterministic`, `test_trade_uuid_deterministic`, `test_signal_confidence_bounds`, `test_market_input_price_positive`, `test_execution_decision_actions`.

### [x] Tarea 1.4: Crear `SignalStrategy` ABC en `core/signal_strategy.py`

**Archivos**: `src/trady_ai/core/signal_strategy.py` | **Dep**: 1.3
**Qué**: Clase abstracta `SignalStrategy(ABC)` con 4 abstractmethods: `name` (property), `evaluate(state) → Signal`, `update(state) → None`, `is_ready() → bool`. Documentación del contrato: evaluate() + update() son determinísticos; `not is_ready()` → Signal(NEUTRAL, 0.0).
**CA**: `SignalStrategy()` → `TypeError`; clase concreta que implementa los 4 métodos se instancia sin error.
**Tests**: `test_signal_strategy_cannot_instantiate`, `test_signal_strategy_interface`.

### [x] Tarea 1.5: Actualizar `conftest.py` con fixtures del core

**Archivos**: `tests/conftest.py`, `tests/fixtures/` (CSV de prueba) | **Dep**: 1.3
**Qué**: Agregar fixtures: `runtime_config` (default), `market_inputs` (lista de inputs sample), `csv_path(tmp_path)` (crea CSV temporal de 100 ticks), `tmp_db_with_tables(tmp_db)` (llama init_core_tables). Crear archivo CSV fixture simple en `tests/fixtures/sample_100.csv` con 100 filas de precio sinusoidal.
**CA**: Fixtures usan `tmp_path` sin filesystem real; `csv_path` produce CSV válido para `read_csv`.
**Tests**: Ninguno (infraestructura de testing).

---

## Phase 2: Strategy & State (5 tareas) — COMPLETE ✅

### [x] Tarea 2.1: Crear `MarkovStrategy` en `core/markov_strategy.py`

**Archivos**: `src/trady_ai/core/markov_strategy.py` | **Dep**: 1.3, 1.4
**Qué**: `MarkovStrategy(SignalStrategy)` con matriz `np.zeros((3,3), dtype=np.int64)`. `update()`: incrementa contadores de transición entre estados. `evaluate()`: calcula probs via `row / row.sum()`, `np.argmax` para dirección. `is_ready()`: `_total_obs >= warmup_ticks`. `STATE_INDEX = {"UP": 0, "DOWN": 1, "NEUTRAL": 2}`. Sin randomness, sin seeding.
**CA**: 50 pre-warmup ticks → NEUTRAL/0.0; tick 51+ → señal válida. Misma secuencia de estados → mismo UUID de señal (determinístico). Empate en argmax → primer índice.
**Tests**: `test_markov_cold_start`, `test_markov_transition_matrix`, `test_markov_determinism`, `test_markov_argmax_tiebreak`, `test_markov_no_transitions_from_current`, `test_markov_is_ready`.

### [x] Tarea 2.2: Crear `MarketStateTracker` en `core/state.py`

**Archivos**: `src/trady_ai/core/state.py` | **Dep**: 1.3
**Qué**: `MarketStateTracker.__init__(threshold_pct)`. `update(market_input) → MarketState`: clasifica UP/DOWN/NEUTRAL según `(new - prev) / prev > threshold`. Primer tick → NEUTRAL. `get_state(market_id) → MarketState | None`. Estado interno: `_states: dict[str, MarketState]`.
**CA**: Primer tick → NEUTRAL/previous_state=None. Subida >0.1% → UP. Bajada >0.1% → DOWN. Dos mercados independientes no contaminan estados.
**Tests**: `test_state_tracker_first_tick_neutral`, `test_state_tracker_up`, `test_state_tracker_down`, `test_state_tracker_neutral`, `test_state_tracker_transition`, `test_state_tracker_multiple_markets`, `test_state_tracker_get_state_unknown`.

### [x] Tarea 2.3: Crear `normalize()` en `core/normalization.py`

**Archivos**: `src/trady_ai/core/normalization.py` | **Dep**: 1.3
**Qué**: Función `normalize(market_input) → MarketInput`: timestamp naive → UTC; timestamp con tz → convertir a UTC; market_id → strip().lower(); source vacío → "csv". Idempotente.
**CA**: Timestamp naive `2024-01-01T12:00:00` → UTC con tzinfo. `market_id=" BTC-USD "` → `"btc-usd"`. Normalizar dos veces da mismo resultado.
**Tests**: `test_normalization_timestamps_naive`, `test_normalization_timestamps_with_tz`, `test_normalization_decimals`, `test_normalization_market_id`, `test_normalization_idempotent`.

### [x] Tarea 2.4: Crear `read_csv()` en `core/ingestion.py`

**Archivos**: `src/trady_ai/core/ingestion.py` | **Dep**: 1.3
**Qué**: `read_csv(path) → list[MarketInput]`: `csv.DictReader`, valida columnas `{timestamp, market_id, price, volume}`, parsea cada fila. `FileNotFoundError` si no existe. `ValueError` si faltan columnas, timestamp inválido, price inválido, o CSV vacío. Orden de filas preservado.
**CA**: CSV bien formado → lista con valores correctos. CSV sin columna "volume" → ValueError. Archivo inexistente → FileNotFoundError. 100 filas → 100 MarketInputs en orden.
**Tests**: `test_ingestion_valid`, `test_ingestion_invalid_columns`, `test_ingestion_missing_file`, `test_ingestion_empty_csv`, `test_ingestion_invalid_timestamp`, `test_ingestion_invalid_price`, `test_ingestion_order_preserved`.

### [x] Tarea 2.5: Actualizar `core/__init__.py` con re-exports

**Archivos**: `src/trady_ai/core/__init__.py` | **Dep**: 2.1, 2.2, 2.3, 2.4
**Qué**: Reemplazar placeholder docstring con imports de todos los módulos core: `MarketInput`, `MarketState`, `Signal`, `Position`, `Trade`, `ExecutionDecision`, `SignalStrategy`, `MarkovStrategy`, `MarketStateTracker`, `normalize`, `read_csv`, `RiskEnforcer`, `PositionManager`, `ExecutionEngine`, `ExecutionResult`, `init_core_tables`, `replay`, `verify_replay`, `compute_summary`.
**CA**: `from trady_ai.core import ExecutionEngine` funciona sin error. `from trady_ai.core import *` no rompe namespaces.
**Tests**: Ninguno (verificación de import).

---

## Phase 3: Pipeline & Engine (6 tareas)

### [x] Tarea 3.1: Crear `RiskEnforcer` en `core/risk.py`

**Archivos**: `src/trady_ai/core/risk.py` | **Dep**: 1.2, 1.3
**Qué**: `RiskEnforcer.__init__(max_open_positions=1, max_position_size=Decimal("1000.00"))`. `evaluate(signal, positions, config) → ExecutionDecision`: 5 checks — NEUTRAL→HOLD, max open positions, position size limit, stop loss (current < entry * (1 - stop_loss_pct)), duplicate market. Fail-fast: `config.position_size <= 0` → `ValueError`.
**CA**: Signal LONG sin posiciones → OPEN_LONG. Signal LONG con 1 abierta (max=1) → REJECT. Posición LONG con price < 95% entry → CLOSE. Signal NEUTRAL → HOLD. `position_size=0` espera excepción.
**Tests**: `test_risk_enforcer_allow`, `test_risk_enforcer_reject_max_positions`, `test_risk_enforcer_reject_duplicate_market`, `test_risk_enforcer_neutral_hold`, `test_risk_enforcer_stop_loss`, `test_risk_enforcer_fail_fast_invalid_config`.

### [x] Tarea 3.2: Crear `PositionManager` en `core/position_manager.py`

**Archivos**: `src/trady_ai/core/position_manager.py` | **Dep**: 1.2, 1.3
**Qué**: `PositionManager` con `_positions: dict[UUID, Position]`. `open_position(signal, price, size, config) → Position`: UUID5 determinístico, status=OPEN. `close_position(position, exit_price, config) → Position`: calcula PnL, status=CLOSED. `compute_pnl(entry, exit, size, cost_pct, direction) → Decimal`: fórmula LONG/SHORT con cost. get_open_positions(), get_all_positions().
**CA**: LONG entry=100 exit=110 size=10 cost=0% → PnL=1.0. SHORT entry=100 exit=90 size=10 → PnL=1.0. Cost 0.1% aplicado correctamente. Abrir→cerrar→status=CLOSED.
**Tests**: `test_position_manager_pnl_long_profit`, `test_position_manager_pnl_long_loss`, `test_position_manager_pnl_short_profit`, `test_position_manager_pnl_with_cost`, `test_position_manager_round_close`, `test_position_manager_get_open`.

### [x] Tarea 3.3: Crear `ExecutionEngine` en `core/engine.py`

**Archivos**: `src/trady_ai/core/engine.py` | **Dep**: 2.2, 2.3, 3.1, 3.2, 3.4 (persistence), 3.5 (observability), 1.2, 1.4
**Qué**: `ExecutionEngine.__init__(config, db, dry_run=True)`: crea StateTracker, RiskEnforcer, PositionManager. `run(inputs, strategy) → ExecutionResult`: pipeline de 9 pasos por tick (normalize → state → strategy.update → strategy.evaluate → risk → execute → persist → log). `ExecutionResult`: dataclass con decisions, trades, signals, final_positions, summary_stats. Fail-fast: excepción se propaga.
**CA**: CSV completo → ExecutionResult con signals + decisions + trades. Mismo CSV 2 veces → resultados idénticos. Primeros 50 ticks → cero señales no-NEUTRAL. Input inválido → excepción propagada.
**Tests**: `test_engine_pipeline`, `test_engine_determinism`, `test_engine_cold_start_no_signals`, `test_engine_fail_fast`.

### [x] Tarea 3.4: Crear `persistence.py` — 5 tablas + funciones persist

**Archivos**: `src/trady_ai/core/persistence.py` | **Dep**: 1.3
**Qué**: `init_core_tables(db)`: CREATE TABLE IF NOT EXISTS × 5 (market_states, signals, positions, trades, execution_log). Schemas de la spec: TEXT para Decimales, UUID5 TEXT PK, CHECK constraints. Funciones: `persist_market_state`, `persist_signal`, `persist_position` (upsert por id), `persist_trade`, `persist_execution_log`, `load_execution_log` (ORDER BY tick_number). Sin RANDOM(), sin CURRENT_TIMESTAMP.
**CA**: `init_core_tables` 2 veces → idempotente. Persist Signal → leer → mismo Signal. Precio Decimal "100.123456789" → mismo string. 3 ticks → orden correcto.
**Tests**: `test_persistence_roundtrip`, `test_persistence_decimal_precision`, `test_persistence_idempotent_init`, `test_persistence_execution_log_order`.

### [x] Tarea 3.5: Crear `observability.py` — `compute_summary`

**Archivos**: `src/trady_ai/core/observability.py` | **Dep**: 1.3
**Qué**: `compute_summary(decisions, trades, positions) → dict`: total_signals, signals_by_direction (Counter), total_trades, open_positions, closed_positions, win_rate (wins/closed), total_pnl (suma), max_drawdown (recorrer closed cronológicamente, track peak-to-trough). Decimal para P&L, float para win_rate.
**CA**: Sin datos → summary con ceros. 3 trades 2 wins → win_rate=0.666... P&L negativo → total_pnl negativo. max_drawdown tracking correcto.
**Tests**: `test_compute_summary_empty`, `test_compute_summary_win_rate`, `test_compute_summary_total_pnl`, `test_compute_summary_signals_by_direction`.

### [x] Tarea 3.6: Tests de integración — persistence + engine pipeline

**Archivos**: `tests/integration/test_core_pipeline.py` | **Dep**: 3.3, 3.4, 3.5
**Qué**: 4 tests de integración: (1) persistence roundtrip completo — crear Signal, persistir, leer, comparar. (2) engine pipeline con CSV temporal de 100 ticks → decisions, trades, signals no vacíos. (3) determinism — mismo CSV ejecutado 2 veces → resultados idénticos (field-by-field). (4) cold start — primeros 50 ticks → zero signals no-NEUTRAL.
**CA**: 4/4 tests pasan. Coverage integración ≥ 85%.
**Tests**: `test_persistence_complete_roundtrip`, `test_engine_pipeline_integration`, `test_engine_determinism_integration`, `test_engine_cold_start_integration`.

---

## Phase 4: Assembly & CLI (3 tareas)

### [x] Tarea 4.1: Crear `replay.py` — replay + verify_replay

**Archivos**: `src/trady_ai/core/replay.py` | **Dep**: 3.3, 3.4
**Qué**: `replay(db, strategy, config) → ExecutionResult`: lee execution_log, reconstruye MarketInputs, crea engine fresh, ejecuta. `verify_replay(original, replayed) → bool`: compara decisions, signals, trades field-by-field. Mismatch → `AssertionError` con diff.
**CA**: engine.run → persist → replay → verify_replay == True. Replay 2 veces → mismos resultados. Resultados diferentes → AssertionError.
**Tests**: `test_replay`, `test_replay_determinism`, `test_verify_replay_mismatch`.

### [x] Tarea 4.2: Actualizar `settings.py` + `pyproject`

**Archivos**: `src/trady_ai/config/settings.py` | **Dep**: 1.2
**Qué**: Agregar 5 campos default a Settings: `default_threshold_pct`, `default_warmup_ticks`, `default_position_size` (str), `default_transaction_cost_pct`, `default_stop_loss_pct`. Método `get_runtime_config() → RuntimeConfig` que construye desde defaults. `position_size` como str (env var) → Decimal en RuntimeConfig.
**CA**: `get_settings().get_runtime_config()` retorna RuntimeConfig con defaults. Sobrescribir env var → RuntimeConfig refleja cambio.
**Tests**: `test_settings_runtime_config_defaults`, `test_settings_runtime_config_override`.

### [x] Tarea 4.3: Implementar CLI commands (backtest, analyze, run)

**Archivos**: `src/trady_ai/cli/main.py` | **Dep**: 2.4, 3.3, 4.2
**Qué**: `trady-ai backtest --input <csv> [--threshold] [--warmup] [--position-size] [--transaction-cost] [--stop-loss]`: lee CSV, crea RuntimeConfig + MarkovStrategy + Engine, ejecuta, muestra summary. `trady-ai analyze --market <id>`: lee últimas señales de DB + P&L. `trady-ai run --market <id>`: stub que imprime "Simulated execution (dry_run=True)". `validate_secrets` NO invocado.
**CA**: `backtest` con CSV temporal → output con summary stats. `backtest` con archivo inexistente → exit code error. `analyze` con datos en DB → muestra señales. `run` → "Simulated execution".
**Tests**: `test_backtest_command`, `test_backtest_missing_file`, `test_analyze_with_data`, `test_run_dry_run`.

---

## Phase 5: Verification (1 tarea)

### [x] Tarea 5.1: Verification final — test suite + lint + types + coverage

**Archivos**: Todos los anteriores | **Dep**: 1.1–4.3
**Qué**: Ejecutar batería completa: `pytest --cov=trady_ai --cov-report=term-missing` → todos pasan, ≥ 80% coverage; `ruff check .` → 0 errores; `mypy src/` → 0 errores. Validar invariantes: sin async en core, sin APIs, sin inteligencia, sin hidden retries, sin probabilistic paths.
**CA**: 54+ tests pasan. Coverage ≥ 80%. ruff 0 errores. mypy 0 errores. Deterministic contract verificado con test_engine_determinism.
**Tests**: Todos los anteriores.

---

## Resumen

| Fase | Tareas | Focus |
|------|--------|-------|
| Phase 1: Foundation | ✅ 1.1–1.5 (5) | pyproject, runtime_config, models, ABC, conftest |
| Phase 2: Strategy & State | ✅ 2.1–2.5 (5) | markov, state tracker, normalization, ingestion, core re-exports |
| Phase 3: Pipeline & Engine | ✅ 3.1–3.6 (6) | risk, position_manager, engine, persistence, observability, integration tests |
| Phase 4: Assembly & CLI | ✅ 4.1–4.3 (3) | replay, settings, CLI backtest/analyze/run |
| Phase 5: Verification | ✅ 5.1 (1) | Full test suite + lint + types + coverage |
| **Total** | **✅ 20/20 tareas** | |

---

## Dependency Graph

```
1.1 (pyproject +numpy)
  │
1.2 (runtime_config) ──┐
  │                    │
1.3 (models) ──────────┤
  │                    │
1.4 (signal_strategy) ─┤
  │                    │
1.5 (conftest/fixtures) │
  │                    │
  ├── 2.1 (markov) ────┤
  ├── 2.2 (state) ─────┤
  ├── 2.3 (normalize) ─┤
  ├── 2.4 (ingestion) ─┤
  │                    │
  ├── 3.1 (risk) ──────┤
  ├── 3.2 (pos_manager)┤
  ├── 3.4 (persistence)┤
  ├── 3.5 (observ) ────┤
  │                    │
  ├── 3.3 (engine) ◄───┼── Depende de 2.2, 2.3, 3.1, 3.2, 3.4, 3.5
  │                    │
  ├── 3.6 (int tests) ◄┼── engine + persistence + observability
  │                    │
  ├── 4.1 (replay) ◄───┤
  ├── 4.2 (settings) ──┤
  ├── 4.3 (CLI) ◄──────┼── ingestion + engine + settings
  │                    │
  └── 5.1 (verify) ◄───┼── ALL
                       │
[2.5: core/__init__] ───┘  (depende de 2.1–2.4 y 3.1–3.5)
```

## Orden de ejecución recomendado

1. **Fase 1** (1.1 → 1.2 → 1.3 → 1.4 → 1.5): Foundation completa. Al llegar acá tenés numpy instalado, modelos Pydantic compilando, ABC lista, conftest con fixtures.
2. **Fase 2** (2.1 → 2.2 → 2.3 → 2.4 → 2.5): Strategy + State. Independientes entre sí (dependen solo de Fase 1). `core/__init__` se actualiza al final.
3. **Fase 3** (3.1 → 3.2 → 3.4 → 3.5 → 3.3 → 3.6): Pipeline. risk + position_manager son independientes. persistence + observability también. **engine** (3.3) depende de todos los anteriores — hacerlo al final de la fase. Integration tests (3.6) cierran la fase.
4. **Fase 4** (4.1 → 4.2 → 4.3): Assembly. replay depende de engine+persistence. settings es independiente. CLI depende de ingestion+engine+settings.
5. **Fase 5** (5.1): Verification final.

## Plan de PRs encadenados (stacked-to-main)

| PR | Tareas | Estimado | Depende de |
|----|--------|----------|------------|
| PR 1 → main | 1.1, 1.2, 1.3, 1.4, 1.5 | ~380 lines | — |
| PR 2 → main | 2.1, 2.2, 2.3, 2.4, 2.5 | ~450 lines | PR 1 |
| PR 3 → main | 3.1, 3.2, 3.3, 3.4, 3.5, 3.6 | ~500 lines | PR 2 |
| PR 4 → main | 4.1, 4.2, 4.3, 5.1 | ~540 lines | PR 3 |

Cada PR mergea a `main` secuencialmente. PR 2 no se abre hasta que PR 1 esté mergeado. Así el diff de cada PR es revisable dentro del budget de 400 líneas (PR 1 está por debajo; PR 2, 3, 4 están cerca del límite y pueden requerir atención del reviewer). Si algún PR excede 400 líneas significativamente, dividir: ej. PR 3 podría separar en 3a (risk+pos_manager+persistence+observability) y 3b (engine+int tests).
