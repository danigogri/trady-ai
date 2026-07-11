# Design: 003 — Polymarket Integration

## Technical Approach

Stateless PolymarketAdapter + stateful EventCapture in a background thread. Events flow WS → adapter → capture → event_store (SQLite append-only). Engine reads via `run_from_store()` — pipeline unchanged. Dry-run first, live second, same architecture.

## Architecture Decisions

| Decision | Options (tradeoffs) | Chosen | Rationale |
|----------|--------------------|--------|-----------|
| WS library | `websockets` (mature async) vs `websocket-client` (blocking-only) vs raw asyncio | `websockets` | Pure async, well-typed, same pattern as httpx for HTTP. Blocking WS lib would fight the thread boundary. |
| HTTPX client mode | `AsyncClient` (single-client) vs `Client` sync for REST + `asyncio.run()` for WS | **Sync Client for REST, async for WS** | REST is called from sync core. WS thread uses its own `asyncio.run()` boundary — two separate clients, correct isolation. |
| WS thread model | `threading.Thread` (isolates async) vs pure asyncio loop (contaminates core) | `threading.Thread` | Core stays 100% sync. Async lives only inside the adapter thread boundary. Matches RFC-002. |
| Dedup strategy | `INSERT OR IGNORE` (sqlite_utils native) vs `ON CONFLICT DO NOTHING` (SQL-standard) | `INSERT OR IGNORE` | Matches sqlite_utils idiom in existing code. Same SQL semantics, no raw SQL required. |
| raw_payload storage | `TEXT` (JSON string) vs typed columns per field | **`TEXT NOT NULL`** | Preserves original platform payload for future Reflection/Intelligence. Schema stays stable when Polymarket API evolves. |
| Reconnect cursor | `MAX(seq)` → translate to timestamp vs `MAX(timestamp)` directly | `MAX(seq)` → timestamp lookup | `seq` is system-controlled, monotonic, deterministic. `timestamp` depends on external clock — duplicates and gaps possible. |

## Data Flow

```
                        ┌──────────────────────────────┐
                        │       Background Thread       │
                        │  ┌─────────────────────────┐  │
Polymarket WS ──────────┼─►│ subscribe_websocket()   │  │
                        │  │   (websockets generator) │  │
                        │  └──────────┬──────────────┘  │
                        │             ▼                 │
                        │  ┌─────────────────────────┐  │
                        │  │  _capture_one(event)     │  │
                        │  │  market_to_input →       │  │
                        │  │  gen event_id →          │  │
                        │  │  append_event → dedup    │  │
                        │  └──────────┬──────────────┘  │
                        └─────────────┼─────────────────┘
                                      ▼
                              ┌───────────────┐
                              │  event_store   │
                              │  (SQLite)      │
                              └───────┬───────┘
                                      │
                                      ▼
                              ┌───────────────┐
                              │  Engine       │
                              │  run_from_    │
                              │  store()      │
                              └───────────────┘
```

### WS Thread Lifecycle

```
start() ──► while _running:
               │
               ├── retry = 0
               ├── while retry < 5:
               │     try:
               │       gen = adapter.subscribe_websocket(market_ids)
               │       for event in gen:
               │         _capture_one(event)     ← dedup inside
               │       # generator exhausted = disconnect
               │       _handle_reconnect(market_ids)  ← REST gap fill
               │       retry = 0  ← successful reconnect resets counter
               │     except (ConnectionError, RemoteProtocolError):
               │       delay = [1,2,4,8,16][retry]
               │       structlog.warning("ws_disconnect", retry, delay)
               │       time.sleep(delay)
               │       retry += 1
               │
               └── retry >= 5:
                     self._error = last_exception
                     _running = False
                     structlog.critical("ws_capture_failed")
                     exit thread
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/trady_ai/adapters/polymarket.py` | Create | `PolymarketAdapter` (stateless, 6 REST + WS generator + 2 mappers) + `EventCapture` (stateful, thread lifecycle) |
| `src/trady_ai/core/persistence.py` | Modify | +6 functions: `init_event_store`, `append_event`, `get_events`, `get_max_seq`, `count_events`, `reset_event_store` |
| `src/trady_ai/core/engine.py` | Modify | +`run_from_store()` — delegates to `run()` |
| `src/trady_ai/config/settings.py` | Modify | +Polymarket fields, `get_active_market_ids()` helper |
| `src/trady_ai/config/runtime_config.py` | Modify | +`execution_mode`, `default_order_type` |
| `src/trady_ai/cli/main.py` | Modify | +`capture` command, `run` → `run_from_store()`, `status` extended |
| `pyproject.toml` | Modify | +`websockets>=13.0` |
| `tests/unit/test_adapter.py` | Create | PolymarketAdapter unit tests |
| `tests/unit/test_capture.py` | Create | EventCapture unit tests |
| `tests/unit/test_persistence_event_store.py` | Create | event_store persistence tests |
| `tests/integration/test_polymarket_pipeline.py` | Create | WS → capture → store → run pipeline |

## Key Interfaces

**event_store schema** (in `persistence.py`):
```python
def init_event_store(db: sqlite_utils.Database) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS event_store (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            market_id TEXT NOT NULL,
            price TEXT NOT NULL,
            volume TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'polymarket',
            raw_payload TEXT NOT NULL,
            captured_at TEXT NOT NULL
        )
    """)
```

**append_event with dedup**:
```python
def append_event(db: sqlite_utils.Database, event: dict) -> int | None:
    try:
        db["event_store"].insert(event, pk="event_id")
        return db["event_store"].last_rowid  # seq from AUTOINCREMENT
    except sqlite_utils.db.IntegrityError:  # UNIQUE violation
        return None
```

**run_from_store** (in `engine.py`):
```python
def run_from_store(self, strategy: SignalStrategy, since_seq: int = 0) -> ExecutionResult:
    from trady_ai.core.persistence import get_events
    inputs = get_events(self._db, since_seq=since_seq)
    return self.run(inputs, strategy)
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit — PolymarketAdapter | `market_to_input`, `order_to_trade`, `place_order` validation | Pure functions — direct call with known inputs. No network. |
| Unit — EventCapture | `_capture_one` insert, dedup, `start`/`stop` lifecycle, `reset` guard | Mock adapter.subscribe_websocket with known events. Real sqlite_utils in tmp_path. |
| Unit — persistence | `append_event` insert/dedup, `get_events` ordering, `get_max_seq`, `reset` | Direct function calls against sqlite_utils in tmp_path. |
| Unit — Settings | Polymarket defaults, `get_active_market_ids` parsing | Settings constructor with env var monkeypatch. |
| Integration | WS mock → EventCapture → event_store → run_from_store → ExecutionResult | Full pipeline with mocked WS generator. Verify dedup, seq continuity, replay determinism. |
| Integration | Reconnect gap fill | Simulate WS disconnect: fill store with seq 1-5, trigger reconnect → verify REST gap events appended (seq 6+). |

## Rollout

**Iteration 1 — dry_run**: Deploy adapter + capture + event_store. Pipeline runs without signing. WS capture + replay verified. Secrets may be empty.

**Iteration 2 — live**: Enable `validate_secrets()` guard, `place_order`/`cancel_order` real credentials. Same code paths — only the signing changes.

**Rollback**: Stop capture thread. Delete `adapters/polymarket.py`. Revert persistence/settings/pyproject. Verify `backtest` and `status` still work.
