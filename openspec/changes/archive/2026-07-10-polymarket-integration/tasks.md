# Tasks: Polymarket Integration (Fase 2)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,386 (8 nuevos + 4 modificados + 6 test files) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Foundation → PR 2: Adapter → PR 3: Capture+Engine → PR 4: CLI+Integration |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

```
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | PR | Notes |
|------|------|----|-------|
| 1 | Foundation: persistence + config + pyproject | PR 1 → main | ~366 lines; base de todas las dep |
| 2 | PolymarketAdapter (stateless, REST+WS+mappers) | PR 2 → main | ~290 lines; depende de PR 1 |
| 3 | EventCapture + Engine run_from_store | PR 3 → main | ~390 lines; depende de PR 2 |
| 4 | CLI capture/run/status + integration tests + verify | PR 4 → main | ~340 lines; depende de PR 3 |

---

## Phase 1: Foundation — Persistence & Config (PR 1)

### [x] Tarea 1.1: Agregar `websockets>=13.0` a pyproject.toml

**Archivos**: `pyproject.toml` | **Dep**: —
**Qué**: Agregar `"websockets>=13.0"` a `dependencies`.
**CA**: `pip install -e "."` no falla; `from websockets import connect` funciona.
**Tests**: Ninguno (verificación manual con pip install).

### [x] Tarea 1.2: Agregar `event_store` table + 6 funciones a `persistence.py`

**Archivos**: `src/trady_ai/core/persistence.py` | **Dep**: 1.1 (websockets opcional acá pero pyproject sí)
**Qué**: `init_event_store(db)` — CREATE TABLE IF NOT EXISTS event_store (seq INTEGER PK AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, market_id TEXT NOT NULL, price TEXT NOT NULL, volume TEXT NOT NULL, timestamp TEXT NOT NULL, event_type TEXT NOT NULL, source TEXT DEFAULT 'polymarket', raw_payload TEXT NOT NULL, captured_at TEXT NOT NULL). `append_event(db, event) → int | None` — INSERT OR IGNORE con dedup por event_id. `get_events(db, since_seq=0, limit=100) → list[MarketInput]` — SELECT ordenado por seq ASC. `get_max_seq(db) → int` — SELECT MAX(seq) o 0 si vacío. `count_events(db) → int`. `reset_event_store(db)` — DROP + CREATE. `init_core_tables()` también llama a `init_event_store()`.
**CA**: append_event con event_id nuevo → seq; mismo event_id → None. get_events ordenado por seq. get_max_seq en tabla vacía → 0. reset → 0 rows. init idempotente.
**Tests**: `test_persistence_append_event`, `test_persistence_append_dedup`, `test_persistence_get_events`, `test_persistence_get_events_empty`, `test_persistence_get_max_seq`, `test_persistence_count_events`, `test_persistence_reset_event_store`, `test_persistence_init_idempotent`.

### [x] Tarea 1.3: Agregar campos Polymarket a `settings.py`

**Archivos**: `src/trady_ai/config/settings.py` | **Dep**: 1.2 (para get_runtime_config consistency)
**Qué**: Agregar `polymarket_api_key: str = ""`, `polymarket_secret: str = ""`, `polymarket_passphrase: str = ""`, `polymarket_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"`, `polymarket_rest_url: str = "https://clob.polymarket.com"`, `active_markets: str = ""`. Método `get_active_market_ids() → list[str]` que split por coma y strip.
**CA**: Settings() con defaults → api_key vacío, ws_url default. get_active_market_ids("0xabc, 0xdef") → ["0xabc", "0xdef"]. active_markets="" → [].
**Tests**: `test_settings_polymarket_defaults`, `test_settings_get_active_market_ids`, `test_settings_get_active_market_ids_empty`.

### [x] Tarea 1.4: Agregar `execution_mode` y `default_order_type` a `runtime_config.py`

**Archivos**: `src/trady_ai/config/runtime_config.py` | **Dep**: —
**Qué**: Agregar `execution_mode: Literal["dry_run", "live"] = "dry_run"`, `default_order_type: Literal["GTC"] = "GTC"`. ValidationError en modo inválido.
**CA**: RuntimeConfig() → execution_mode="dry_run". RuntimeConfig(execution_mode="paper") → ValidationError.
**Tests**: `test_runtime_config_execution_mode`, `test_runtime_config_invalid_mode`.

### [x] Tarea 1.5: Tests de config + persistence

**Archivos**: `tests/unit/test_persistence_event_store.py`, `tests/unit/test_config_polymarket.py` | **Dep**: 1.2, 1.3, 1.4
**Qué**: persistence test file: 8 tests contra sqlite_utils en tmp_path. Config test file: 5 tests (settings defaults, get_active_market_ids × 2, runtime_config mode, runtime_config invalid). validate_secrets: 3 tests (dry_run ok, live missing, live complete).
**CA**: 16 tests pasan, coverage ≥ 90% en persistence.py + settings.py + runtime_config.py.
**Tests**: Los 16 tests descritos arriba.

---

## Phase 2: Adapter — PolymarketAdapter (PR 2)

### [x] Tarea 2.1: Crear `adapters/__init__.py`

**Archivos**: `src/trady_ai/adapters/__init__.py` | **Dep**: —
**Qué**: Reemplazar placeholder con `from trady_ai.adapters.polymarket import PolymarketAdapter, EventCapture` (EventCapture se define en PR 3, usar import condicional o forward ref).
**CA**: `from trady_ai.adapters import PolymarketAdapter` funciona sin error.
**Tests**: Ninguno (verificación de import).

### [x] Tarea 2.2: Crear `PolymarketAdapter` en `adapters/polymarket.py`

**Archivos**: `src/trady_ai/adapters/polymarket.py` | **Dep**: 1.2, 1.3
**Qué**: Clase `PolymarketAdapter` stateless con: `__init__(rest_url, ws_url, api_key, secret, passphrase)`. 6 REST methods con httpx sync: `get_markets() → list[dict]`, `get_market_data(id) → dict`, `get_order_book(id) → dict`, `place_order(id, side, price, size) → dict`, `cancel_order(id) → dict`, `get_open_orders(id) → list[dict]`. 1 WS generator: `subscribe_websocket(ids) → Generator[dict]` (usa websockets con asyncio.run internamente). 2 pure mappers: `market_to_input(raw) → MarketInput`, `order_to_trade(raw, signal_id, position_id, dry_run) → Trade`. Validaciones: side in BUY/SELL, price > 0, size > 0, market_id not empty. No state, no caching, no retries, fail-fast.
**CA**: market_to_input con raw válido → MarketInput con source="polymarket". market_to_input con keys faltantes → KeyError. place_order con side inválido → ValueError sin HTTP call. subscribe_websocket([]) → ValueError.
**Tests**: `test_adapter_market_to_input`, `test_adapter_market_to_input_missing_keys`, `test_adapter_order_to_trade`, `test_adapter_place_order_validation`, `test_adapter_subscribe_empty_markets`.

---

## Phase 3: Capture + Engine (PR 3)

### [x] Tarea 3.1: Agregar `EventCapture` a `adapters/polymarket.py`

**Archivos**: `src/trady_ai/adapters/polymarket.py` | **Dep**: 2.2
**Qué**: Clase `EventCapture` stateful con: `__init__(adapter, db)`. `start(market_ids) → None` — spawn daemon thread con reconnect loop (max 5 retries, backoff 1/2/4/8/16s). `stop() → None` — set flag, join thread. `_capture_one(raw_event) → int | None` — translate via adapter.market_to_input, generate event_id, append_event, dedup. `_handle_reconnect(market_ids) → None` — MAX(seq) → timestamp lookup → REST gap fill → reconnect WS. `reset() → None` — DROP+recreate (dev only). Properties: is_running, last_seq, error.
**CA**: start → thread running, is_running True. start dos veces → RuntimeError. _capture_one evento nuevo → seq, duplicado → None. reset en prod → RuntimeError. stop idempotente.
**Tests**: `test_capture_insert_new`, `test_capture_dedup`, `test_capture_start_stop`, `test_capture_start_twice`, `test_capture_reset_dev`, `test_capture_reset_prod`.

### [x] Tarea 3.2: Agregar `run_from_store()` a `engine.py`

**Archivos**: `src/trady_ai/core/engine.py` | **Dep**: 1.2, 1.4
**Qué**: Método `run_from_store(strategy, since_seq=0) → ExecutionResult` en ExecutionEngine. Lee eventos desde event_store via `get_events()`, delega a `self.run()`. since_seq < 0 → ValueError.
**CA**: run_from_store con 10 events → ExecutionResult con 10 decisions. since_seq=5 → solo events 6-10. Mismo event_store 2 veces → idéntico resultado.
**Tests**: `test_engine_run_from_store`, `test_engine_run_from_store_since_seq`.

### [x] Tarea 3.3: Tests de capture + engine

**Archivos**: `tests/unit/test_capture.py`, `tests/unit/test_engine.py` | **Dep**: 3.1, 3.2
**Qué**: capture test file: 6 tests con sqlite_utils en tmp_path, mock adapter. engine test file: 2 tests con event_store poblado → run_from_store verifica salida.
**CA**: 8 tests pasan, capture coverage ≥ 85%, engine run_from_store coverage 100%.
**Tests**: Los 8 tests descritos arriba.

---

## Phase 4: CLI + Integration + Verify (PR 4)

### [x] Tarea 4.1: Implementar `capture` command + modificar `run` y `status` en CLI

**Archivos**: `src/trady_ai/cli/main.py` | **Dep**: 3.1, 3.2, 1.3, 1.4
**Qué**: `trady-ai capture [--reset] [--markets]`: inicializa Settings, RuntimeConfig, EventCapture, llama start con active_market_ids. Corre hasta Ctrl+C (signal handler). `--reset`: llama EventCapture.reset() antes de start (dev only). `trady-ai run --market X --since-seq 0`: llama `validate_secrets`, crea Engine, ejecuta `run_from_store()`, muestra summary. `trady-ai status`: agrega "Event Store: N events (max_seq: M)", "Capture: running/stopped", "Active markets: [...]", "Execution mode: dry_run/live". Secrets NUNCA en output.
**CA**: `capture` persiste eventos a event_store hasta Ctrl+C. `capture --reset` dropea tabla antes (dev). `capture --reset` en prod → error. `run --market X` procesa event_store. `status` muestra stats + capture state sin secrets.
**Tests**: `test_capture_cli_integration`, `test_run_cli_from_store`.

### [x] Tarea 4.2: Agregar `validate_secrets()` al CLI flow

**Archivos**: `src/trady_ai/cli/main.py` y nuevo helper | **Dep**: 1.3, 1.4
**Qué**: Función `validate_secrets(settings, execution_mode) → None`. Si dry_run → return. Si live → verifica api_key, secret, passphrase, active_markets no vacíos. Llamada antes de WS connect (capture) y antes de run. Si faltan → ValueError descriptivo.
**CA**: dry_run con secrets vacíos → pasa. live con api_key vacío → ValueError. live con todo completo → pasa.
**Tests**: `test_validate_secrets_dry_run`, `test_validate_secrets_live_missing`, `test_validate_secrets_live_complete`.

### [x] Tarea 4.3: Integration tests — pipeline completo

**Archivos**: `tests/integration/test_polymarket_pipeline.py` | **Dep**: 3.1, 3.2, 4.1
**Qué**: 8 tests: (1) WS mock → EventCapture → event_store → run_from_store → ExecutionResult. (2) Dedup: mismo event_id 2 veces → 1 row. (3) Replay: misma event_store → mismos outputs. (4) Reconnect gap fill: seq 1-5 → disconnect → REST gap → seq 6+. (5-6) CLI integration con CliRunner. (7) Determinism: mismos eventos insertados → mismo seq assignment. (8) Determinism: run_from_store 2 veces → idéntico resultado.
**CA**: 8/8 tests pasan. Coverage integración ≥ 80%.
**Tests**: Los 8 tests descritos arriba.

### [x] Tarea 4.4: Verification final

**Archivos**: Todos los anteriores | **Dep**: 1.1–4.3
**Qué**: `pytest --cov=trady_ai --cov-report=term-missing` → todos pasan (37 tests). `ruff check .` → 0 errores. `mypy src/` → 0 errores. Validar invariantes: core NO importa de adapters, no async en core, append-only event_store, secrets no logueados.
**CA**: 37+ tests pasan. Coverage ≥ 80%. ruff 0 errores. mypy 0 errores.
**Tests**: Todos los anteriores.

---

## Resumen

| Fase | Tareas | PR | Focus |
|------|--------|----|-------|
| Phase 1: Foundation | 1.1–1.5 (5) | PR 1 → main | pyproject, event_store, settings, runtime_config, tests |
| Phase 2: Adapter | 2.1–2.2 (2) | PR 2 → main | PolymarketAdapter + REST/WS/mappers + tests |
| Phase 3: Capture+Engine | 3.1–3.3 (3) | PR 3 → main | EventCapture, run_from_store, tests |
| Phase 4: CLI+Integration | 4.1–4.4 (4) | PR 4 → main | CLI commands, validate_secrets, integration tests, verify |
| **Total** | **14 tareas** | **4 PRs** | |

### Orden de ejecución recomendado

1. **Phase 1** (1.1 → 1.2 → 1.3 → 1.4 → 1.5): Foundation. persistence lista, settings con campos Polymarket, runtime_config con execution_mode. Testeado.
2. **Phase 2** (2.1 → 2.2): PolymarketAdapter puro. Stateless, testeable sin red. Mappers con escenarios de spec.
3. **Phase 3** (3.1 → 3.2 → 3.3): EventCapture (thread lifecycle, dedup, reconnect) + engine.run_from_store. Capture conecta adapter al store; engine consume del store.
4. **Phase 4** (4.1 → 4.2 → 4.3 → 4.4): CLI commands, validate_secrets guard, integration tests (pipeline completo, dedup, replay, determinism), verification final.

### Plan de PRs encadenados (stacked-to-main)

| PR | Tareas | Estimado | Depende de |
|----|--------|----------|------------|
| PR 1 → main | 1.1, 1.2, 1.3, 1.4, 1.5 | ~366 lines | — |
| PR 2 → main | 2.1, 2.2 | ~290 lines | PR 1 |
| PR 3 → main | 3.1, 3.2, 3.3 | ~390 lines | PR 2 |
| PR 4 → main | 4.1, 4.2, 4.3, 4.4 | ~340 lines | PR 3 |

Cada PR mergea a `main` secuencialmente. PR 2 no se abre hasta que PR 1 esté mergeado. El diff acumulado de PR 4 será ~1,386 líneas, pero cada diff individual está en o por debajo del budget de 400 líneas.

### Dependency Graph

```
1.1 (pyproject +websockets)
  │
1.2 (persistence: event_store +6 funcs) ──┐
  │                                       │
1.3 (settings: +6 Polymarket fields) ─────┤
  │                                       │
1.4 (runtime_config: +execution_mode) ────┤
  │                                       │
1.5 (tests: persistence + config) ────────┤
  │                                       │
  ├── 2.1 (adapters/__init__.py) ─────────┤
  ├── 2.2 (PolymarketAdapter) ────────────┤
  │                                       │
  ├── 3.1 (EventCapture) ◄────────────────┤
  ├── 3.2 (engine.run_from_store) ◄───────┤
  │                                       │
  ├── 3.3 (capture + engine tests) ◄──────┤
  │                                       │
  ├── 4.1 (CLI: capture/run/status) ◄─────┤
  ├── 4.2 (validate_secrets) ─────────────┤
  ├── 4.3 (integration tests) ◄───────────┤
  │                                       │
  └── 4.4 (verify) ◄──────────────────────┘
```

### Próximo paso

Ready for implementation (sdd-apply). PR 1 → main puede comenzar. La estrategia `stacked-to-main` está pre-acordada. `ask-on-risk`: se pedirá confirmación antes de cada apply.
