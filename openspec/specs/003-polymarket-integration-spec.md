# SDD Spec: 003 — Polymarket Integration (Fase 2)

**RFC de referencia**: RFC-002 (Platform Integration Architecture), RFC-000 (Security & Operational Safety)
**Fase del roadmap**: Fase 2
**Proposal**: `003-polymarket-integration-proposal.md`
**Baseline**: 001-python-bootstrap + 002-deterministic-core
**Boundary**: Adapter + Event Store en infrastructure boundary. Core pipeline determinístico NO cambia.

---

## Deterministic vs Intelligence Boundary

| Layer | Deterministic | Intelligence |
|-------|--------------|--------------|
| PolymarketAdapter | ✅ Stateless translation, frozen contracts | ❌ No interpretation |
| EventCapture | ✅ Append-only, dedup, seq assignment | ❌ No mutation |
| Event Store | ✅ SQLite append-only, immutable | ❌ No modification |
| Core Engine | ✅ Pipeline unchanged from 002 | ❌ No AI in core |

**Invariant**: External platform adapts to architecture. Architecture NEVER adapts to platform (RFC-002).

---

## Data Flow

```
Polymarket WS ──► PolymarketAdapter (stateless) ──► EventCapture (stateful)
                                                          │
                                                          ▼
                                                    event_store (SQLite)
                                                          │
                                                          ▼
                                              Engine.run_from_store()
                                                          │
                                                          ▼
                                              signals, decisions, trades
```

---

## Module 1: `src/trady_ai/adapters/polymarket.py` — PolymarketAdapter

**Purpose**: Stateless translator between Polymarket CLOB API and internal contracts. Adapts structure, NEVER owns meaning (RFC-002).

### Interface

```python
from decimal import Decimal
from typing import Generator

import httpx

from trady_ai.core.models import MarketInput, Trade


class PolymarketAdapter:
    """Stateless adapter: Polymarket CLOB API → internal contracts.

    Uses httpx directly (no SDKs). All methods are pure translations.
    No state, no caching, no retries.
    """

    def __init__(self, rest_url: str, ws_url: str, api_key: str = "",
                 secret: str = "", passphrase: str = ""):
        ...

    # ── REST methods ──

    def get_markets(self) -> list[dict]:
        """GET /markets → list of available markets.

        Returns:
            list[dict]: Each dict has keys: condition_id, question, tokens, active, closed.

        Raises:
            httpx.HTTPStatusError: If API returns non-2xx.
            httpx.ConnectError: If network unreachable.
        """
        ...

    def get_market_data(self, market_id: str) -> dict:
        """GET /market/{market_id} → price, volume, timestamp.

        Args:
            market_id: Polymarket condition ID (e.g. "0x123...").

        Returns:
            dict: Keys: market_id, price (str), volume (str), timestamp (ISO 8601 str),
                  best_bid (str), best_ask (str).

        Raises:
            httpx.HTTPStatusError: 404 if market not found, other non-2xx.
            ValueError: If market_id is empty string.
        """
        ...

    def get_order_book(self, market_id: str) -> dict:
        """GET /order-book?market={market_id} → bids, asks.

        Args:
            market_id: Polymarket Condition ID.

        Returns:
            dict: Keys: market_id, bids (list[dict{price: str, size: str}]),
                  asks (list[dict{price: str, size: str}]), timestamp (ISO 8601).

        Raises:
            httpx.HTTPStatusError: 404 if market not found.
            ValueError: If market_id is empty string.
        """
        ...

    def place_order(self, market_id: str, side: str, price: Decimal,
                    size: Decimal) -> dict:
        """POST /order → place GTC Limit order.

        Args:
            market_id: Polymarket Condition ID.
            side: "BUY" or "SELL".
            price: Limit price (Decimal, > 0).
            size: Order size (Decimal, > 0).

        Returns:
            dict: Keys: order_id (str), status (str), market_id, side,
                  price (str), size (str), order_type ("GTC"), timestamp.

        Raises:
            ValueError: If side not in {"BUY", "SELL"}, price <= 0, size <= 0,
                        market_id empty.
            httpx.HTTPStatusError: If API rejects order.
            RuntimeError: If execution_mode == "live" and credentials missing.
        """
        ...

    def cancel_order(self, order_id: str) -> dict:
        """DELETE /order/{order_id} → cancel pending order.

        Args:
            order_id: Order ID from place_order response.

        Returns:
            dict: Keys: order_id, status ("CANCELLED"), timestamp.

        Raises:
            ValueError: If order_id is empty string.
            httpx.HTTPStatusError: 404 if order not found.
        """
        ...

    def get_open_orders(self, market_id: str) -> list[dict]:
        """GET /orders?market={market_id}&status=OPEN → list of open orders.

        Args:
            market_id: Polymarket Condition ID.

        Returns:
            list[dict]: Each dict: order_id, market_id, side, price (str),
                        size (str), status, timestamp.

        Raises:
            httpx.HTTPStatusError: If API returns non-2xx.
        """
        ...

    # ── WebSocket ──

    def subscribe_websocket(self, market_ids: list[str]) -> Generator[dict, None, None]:
        """Connect to WS endpoint, yield parsed events.

        Blocks the calling thread. Yields dicts as they arrive from WS.
        Each dict has keys: market_id, price (str), volume (str),
        timestamp (ISO 8601 str), event_type (str: "tick"|"trade"|"orderbook_update").

        Args:
            market_ids: List of Condition IDs to subscribe.

        Yields:
            dict: Parsed WS event.

        Raises:
            ValueError: If market_ids is empty.
            ConnectionError: If WS connection fails after max retries.
        """
        ...

    # ── Contract mappers (frozen) ──

    def market_to_input(self, raw: dict) -> MarketInput:
        """Map Polymarket API response → MarketInput.

        Args:
            raw: Dict from get_market_data or WS event.
                 Required keys: market_id, price, volume, timestamp.

        Returns:
            MarketInput: With source="polymarket".

        Raises:
            KeyError: If required keys missing from raw.
            ValueError: If price or volume cannot be parsed as Decimal.
        """
        ...

    def order_to_trade(self, raw: dict, signal_id, position_id,
                       dry_run: bool) -> Trade:
        """Map Polymarket order response → Trade.

        Args:
            raw: Dict from place_order response.
                 Required keys: order_id, price, size, timestamp, side.
            signal_id: UUID of the signal that triggered this trade.
            position_id: UUID of the associated position.
            dry_run: Whether this was simulated.

        Returns:
            Trade: With action="OPEN" (BUY) or "CLOSE" (SELL mapped by caller).

        Raises:
            KeyError: If required keys missing.
        """
        ...
```

### Contracts

| Method | Input | Output | Side Effects |
|--------|-------|--------|-------------|
| `get_markets()` | none | `list[dict]` | HTTP GET |
| `get_market_data(id)` | market_id | `dict` | HTTP GET |
| `get_order_book(id)` | market_id | `dict` | HTTP GET |
| `place_order(...)` | market_id, side, price, size | `dict` | HTTP POST |
| `cancel_order(id)` | order_id | `dict` | HTTP DELETE |
| `get_open_orders(id)` | market_id | `list[dict]` | HTTP GET |
| `subscribe_websocket(ids)` | market_ids | `Generator[dict]` | WS connect, yields |
| `market_to_input(raw)` | raw dict | `MarketInput` | None (pure) |
| `order_to_trade(raw, ...)` | raw dict + IDs | `Trade` | None (pure) |

### Deterministic Behavior

- `market_to_input` and `order_to_trade` are **pure functions**: same input → same output.
- REST methods are **idempotent** (GETs) or **explicit** (POST/DELETE). No hidden retries.
- No caching, no memoization, no state mutation.

### Dependencies

- `httpx` (HTTP client, already in pyproject.toml)
- `websockets` (WS client, NEW — added in this phase)
- `trady_ai.core.models` (MarketInput, Trade)
- `decimal.Decimal`

### Scenarios

#### Scenario: market_to_input maps Polymarket response correctly

- GIVEN a raw dict `{"market_id": "0xabc", "price": "0.65", "volume": "1500.00", "timestamp": "2026-07-08T12:00:00Z"}`
- WHEN `adapter.market_to_input(raw)` is called
- THEN returns `MarketInput(market_id="0xabc", price=Decimal("0.65"), volume=Decimal("1500.00"), timestamp=datetime(2026,7,8,12,0,0, tzinfo=UTC), source="polymarket")`

#### Scenario: market_to_input raises on missing keys

- GIVEN a raw dict `{"market_id": "0xabc"}` (missing price, volume, timestamp)
- WHEN `adapter.market_to_input(raw)` is called
- THEN raises `KeyError` with message indicating missing keys

#### Scenario: place_order validates inputs before HTTP call

- GIVEN `side="INVALID"`, `price=Decimal("0.5")`, `size=Decimal("10")`
- WHEN `adapter.place_order("0xabc", "INVALID", ...)` is called
- THEN raises `ValueError("side must be BUY or SELL")` WITHOUT making HTTP request

#### Scenario: subscribe_websocket yields parsed events

- GIVEN a mock WS server sending `{"market_id": "0xabc", "price": "0.70", "volume": "2000", "timestamp": "...", "event_type": "tick"}`
- WHEN `adapter.subscribe_websocket(["0xabc"])` is iterating
- THEN yields `dict` with keys: market_id, price, volume, timestamp, event_type

#### Scenario: subscribe_websocket raises on empty market list

- GIVEN `market_ids=[]`
- WHEN `adapter.subscribe_websocket([])` is called
- THEN raises `ValueError("market_ids must not be empty")`

---

## Module 2: `src/trady_ai/adapters/polymarket.py` — EventCapture

**Purpose**: Stateful orchestrator. Receives raw events from adapter, assigns sequence numbers, persists to event_store, handles dedup and reconnect.

### Interface

```python
import threading
import sqlite_utils

from trady_ai.adapters.polymarket import PolymarketAdapter
from trady_ai.core.persistence import append_event, get_max_seq


class EventCapture:
    """Stateful capture: WS events → event_store (SQLite).

    State:
        _last_seq: int — last assigned sequence number
        _db: sqlite_utils.Database
        _adapter: PolymarketAdapter
        _thread: threading.Thread | None
        _running: bool
    """

    def __init__(self, adapter: PolymarketAdapter, db: sqlite_utils.Database):
        ...

    def start(self, market_ids: list[str]) -> None:
        """Start WS capture in a background thread.

        Spawns a daemon thread that:
        1. Calls adapter.subscribe_websocket(market_ids)
        2. For each yielded event, calls _capture_one(raw_event)
        3. On WS disconnect, calls _handle_reconnect(market_ids)

        Args:
            market_ids: List of Condition IDs to capture.

        Raises:
            ValueError: If market_ids is empty.
            RuntimeError: If capture is already running.
        """
        ...

    def stop(self) -> None:
        """Stop WS capture thread gracefully.

        Sets _running = False, joins thread with timeout.
        Idempotent: calling stop when not running is a no-op.
        """
        ...

    def _capture_one(self, raw_event: dict) -> int | None:
        """Process a single raw event.

        Steps:
        1. Translate: market_input = self._adapter.market_to_input(raw_event)
        2. Generate event_id: f"{raw_event['market_id']}:{raw_event['timestamp']}:{raw_event.get('event_type', 'tick')}"
        3. Build event dict for persistence
        4. Call append_event(self._db, event_dict)
        5. If inserted → update _last_seq, return seq
        6. If duplicate → return None (skip silently)

        Args:
            raw_event: Dict from WS or REST gap fill.

        Returns:
            int | None: Sequence number if inserted, None if duplicate.
        """
        ...

    def _handle_reconnect(self, market_ids: list[str]) -> None:
        """Handle WS disconnection with REST gap fill.

        Steps:
        1. last_ts = SELECT MAX(timestamp) FROM event_store WHERE source='polymarket'
        2. If last_ts is None → no events captured yet, just reconnect
        3. REST fetch historical events from adapter.get_market_data() for each market_id
           since last_ts (adapter provides filtering or client filters)
        4. For each historical event, call _capture_one(event)
        5. Reconnect WS via adapter.subscribe_websocket(market_ids)

        Raises:
            httpx.HTTPStatusError: If REST gap fill fails (propagated, fail-fast).
        """
        ...

    def reset(self) -> None:
        """DROP event_store table and recreate. DEV ONLY.

        Calls reset_event_store(self._db).
        Resets _last_seq to 0.

        Raises:
            RuntimeError: If environment != "development".
        """
        ...

    @property
    def is_running(self) -> bool:
        """Whether capture thread is active."""
        ...

    @property
    def last_seq(self) -> int:
        """Last assigned sequence number."""
        ...
```

### Event ID Generation

```python
event_id = f"{raw_event['market_id']}:{raw_event['timestamp']}:{raw_event.get('event_type', 'tick')}"
```

- **Deterministic**: same event → same event_id → UNIQUE constraint rejects duplicate.
- **Collision-resistant**: market_id + timestamp + event_type is unique per event.

### Reconnect Protocol

```
WS disconnect detected
    │
    ▼
SELECT MAX(timestamp) FROM event_store WHERE source='polymarket'
    │
    ├── None → no gap, reconnect WS directly
    │
    └── last_ts → REST fetch events since last_ts
                    │
                    ▼
              For each gap event:
                _capture_one(event) → INSERT OR IGNORE
                    │
                    ▼
              Reconnect WS from adapter.subscribe_websocket(market_ids)
```

### Deterministic Behavior

- `_capture_one` is deterministic: same raw_event → same event_id → same dedup outcome.
- Sequence numbers are assigned by SQLite AUTOINCREMENT — deterministic given same insertion order.
- Reconnect gap fill uses REST (synchronous, ordered) — no race conditions.

### Dependencies

- `trady_ai.adapters.polymarket` (PolymarketAdapter)
- `trady_ai.core.persistence` (append_event, get_max_seq, reset_event_store)
- `threading` (background WS thread)
- `sqlite_utils`

### Scenarios

#### Scenario: _capture_one inserts new event

- GIVEN event_store is empty, _last_seq = 0
- WHEN `_capture_one({"market_id": "0xabc", "timestamp": "2026-07-08T12:00:00Z", "price": "0.65", "volume": "1500", "event_type": "tick"})` is called
- THEN returns `1` (first seq), event_store has 1 row with seq=1, _last_seq = 1

#### Scenario: _capture_one deduplicates same event_id

- GIVEN event_store has 1 row with event_id = "0xabc:2026-07-08T12:00:00Z:tick"
- WHEN `_capture_one` is called with same raw_event (producing same event_id)
- THEN returns `None`, event_store still has 1 row (INSERT OR IGNORE)

#### Scenario: start spawns background thread

- GIVEN EventCapture is initialized, capture is not running
- WHEN `start(["0xabc"])` is called
- THEN a daemon thread is spawned, `is_running` returns True, WS events are captured asynchronously

#### Scenario: start raises if already running

- GIVEN capture is already running (is_running == True)
- WHEN `start(["0xabc"])` is called again
- THEN raises `RuntimeError("Capture is already running")`

#### Scenario: stop is idempotent

- GIVEN capture is not running
- WHEN `stop()` is called
- THEN no error, no-op

#### Scenario: reconnect fills gap via REST

- GIVEN event_store has events up to timestamp "2026-07-08T12:05:00Z", WS disconnects
- WHEN `_handle_reconnect(["0xabc"])` executes
- THEN REST fetches events since "2026-07-08T12:05:00Z", gap events inserted via _capture_one, WS reconnected

#### Scenario: reset only works in development

- GIVEN environment = "production"
- WHEN `reset()` is called
- THEN raises `RuntimeError("reset is only available in development")`

#### Scenario: reset drops and recreates event_store in dev

- GIVEN environment = "development", event_store has 100 rows
- WHEN `reset()` is called
- THEN event_store is dropped and recreated (0 rows), _last_seq = 0

---

## Module 3: `src/trady_ai/core/persistence.py` — Event Store

**Purpose**: Add `event_store` table and CRUD functions. Append-only, immutable after insertion.

### Schema

```sql
CREATE TABLE IF NOT EXISTS event_store (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    market_id TEXT NOT NULL,
    price TEXT NOT NULL,          -- Decimal as string
    volume TEXT NOT NULL,         -- Decimal as string
    timestamp TEXT NOT NULL,      -- server timestamp (ISO 8601)
    event_type TEXT NOT NULL,     -- 'tick', 'trade', 'orderbook_update'
    source TEXT NOT NULL DEFAULT 'polymarket',
    captured_at TEXT NOT NULL     -- local timestamp (ISO 8601)
);
```

### New Functions

```python
from datetime import datetime, timezone
from decimal import Decimal

import sqlite_utils

from trady_ai.core.models import MarketInput


def init_event_store(db: sqlite_utils.Database) -> None:
    """Create event_store table if not exists. Idempotent.

    Called from init_core_tables() or independently.
    """
    ...


def append_event(db: sqlite_utils.Database, event: dict) -> int | None:
    """Insert event into event_store. Dedup via event_id UNIQUE.

    Args:
        db: Database instance.
        event: Dict with keys: event_id, market_id, price, volume,
               timestamp, event_type, source (default "polymarket").

    Returns:
        int | None: seq if inserted, None if duplicate (event_id exists).

    Raises:
        KeyError: If required keys missing from event dict.
    """
    ...


def get_events(db: sqlite_utils.Database, since_seq: int = 0,
               limit: int = 100) -> list[MarketInput]:
    """Read events from store as MarketInput list.

    Args:
        db: Database instance.
        since_seq: Return events with seq > since_seq. Default 0 = all.
        limit: Max events to return. Default 100.

    Returns:
        list[MarketInput]: Ordered by seq ASC. source="polymarket".

    Raises:
        ValueError: If since_seq < 0 or limit <= 0.
    """
    ...


def get_max_seq(db: sqlite_utils.Database) -> int:
    """Get highest sequence number in event_store.

    Returns:
        int: MAX(seq), or 0 if table is empty.
    """
    ...


def count_events(db: sqlite_utils.Database) -> int:
    """Count total events in event_store.

    Returns:
        int: COUNT(*).
    """
    ...


def reset_event_store(db: sqlite_utils.Database) -> None:
    """DROP event_store and recreate. DEV ONLY.

    Destroys all captured data. Use only for development regeneration.
    """
    ...
```

### Integration with init_core_tables

`init_core_tables()` MUST also call `init_event_store()` so the table is created alongside core tables. This is additive — existing tables are unaffected.

### Deterministic Behavior

- `append_event` uses `INSERT OR IGNORE` — deterministic dedup.
- `get_events` orders by `seq ASC` — deterministic read order.
- `seq` is `AUTOINCREMENT` — monotonically increasing, deterministic for same insertion order.
- All prices stored as TEXT (Decimal strings) — no floating-point.
- `captured_at` uses `datetime.now(timezone.utc)` — the ONLY place where wall clock is used. This is metadata, not execution data.

### Dependencies

- `sqlite_utils`
- `datetime` (captured_at timestamp)
- `trady_ai.core.models` (MarketInput)

### Scenarios

#### Scenario: append_event inserts new event

- GIVEN event_store is empty
- WHEN `append_event(db, {"event_id": "0xabc:2026-07-08T12:00:00Z:tick", "market_id": "0xabc", "price": "0.65", "volume": "1500", "timestamp": "2026-07-08T12:00:00Z", "event_type": "tick"})` is called
- THEN returns `1`, event_store has 1 row with seq=1

#### Scenario: append_event deduplicates via UNIQUE constraint

- GIVEN event_store has row with event_id = "0xabc:2026-07-08T12:00:00Z:tick"
- WHEN `append_event(db, same_event_dict)` is called again
- THEN returns `None`, event_store still has 1 row

#### Scenario: get_events returns MarketInput list ordered by seq

- GIVEN event_store has 3 rows with seq 1, 2, 3
- WHEN `get_events(db, since_seq=1, limit=10)` is called
- THEN returns list of 2 MarketInput objects (seq 2 and 3), ordered by seq ASC

#### Scenario: get_events with empty store

- GIVEN event_store is empty
- WHEN `get_events(db)` is called
- THEN returns empty list `[]`

#### Scenario: get_max_seq on empty store

- GIVEN event_store is empty
- WHEN `get_max_seq(db)` is called
- THEN returns `0`

#### Scenario: reset_event_store drops all data

- GIVEN event_store has 50 rows
- WHEN `reset_event_store(db)` is called
- THEN event_store has 0 rows, table schema is intact

#### Scenario: init_event_store is idempotent

- GIVEN event_store table already exists
- WHEN `init_event_store(db)` is called again
- THEN no error, table unchanged (IF NOT EXISTS)

---

## Module 4: `src/trady_ai/core/engine.py` — Consumer Mode

**Purpose**: Add `run_from_store()` method so Engine can consume from event_store instead of explicit MarketInput list.

### New Method

```python
class ExecutionEngine:
    # ... existing methods unchanged ...

    def run_from_store(self, strategy: SignalStrategy,
                       since_seq: int = 0) -> ExecutionResult:
        """Run engine consuming from event_store instead of explicit input list.

        Reads events from event_store (since_seq onwards), converts to
        MarketInput list, then delegates to self.run().

        Args:
            strategy: SignalStrategy implementation.
            since_seq: Start from events with seq > since_seq. Default 0 = all.

        Returns:
            ExecutionResult: Same structure as run().

        Raises:
            ValueError: If since_seq < 0.
        """
        from trady_ai.core.persistence import get_events
        inputs = get_events(self._db, since_seq=since_seq)
        return self.run(inputs, strategy)
```

### Deterministic Behavior

- `run_from_store` delegates to `run()` — same pipeline, same determinism guarantees.
- Events from event_store are already normalized (source="polymarket", UTC timestamps, Decimal strings).
- Same event_store state + same strategy + same config → same ExecutionResult.

### Scenarios

#### Scenario: run_from_store processes event_store events

- GIVEN event_store has 10 events for market "0xabc"
- WHEN `engine.run_from_store(strategy, since_seq=0)` is called
- THEN returns ExecutionResult with signals/decisions for all 10 events

#### Scenario: run_from_store with since_seq skips earlier events

- GIVEN event_store has events with seq 1-10
- WHEN `engine.run_from_store(strategy, since_seq=5)` is called
- THEN only events with seq 6-10 are processed (5 events)

#### Scenario: run_from_store produces same result as run with equivalent inputs

- GIVEN event_store has events that produce MarketInput list X
- WHEN `engine.run_from_store(strategy)` and `engine.run(X, strategy)` are both called
- THEN both return identical ExecutionResult (field-by-field comparison)

---

## Module 5: `src/trady_ai/config/settings.py` — New Fields

**Purpose**: Add Polymarket connection settings and market configuration.

### New Fields

```python
class Settings(BaseSettings):
    # ... existing fields unchanged ...

    # Polymarket connection (placeholders in dry_run, validated in live)
    polymarket_api_key: str = ""
    polymarket_secret: str = ""
    polymarket_passphrase: str = ""
    polymarket_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    polymarket_rest_url: str = "https://clob.polymarket.com"

    # Market configuration
    active_markets: str = ""  # Comma-separated Condition IDs: "0x123,0x456"
```

### Validation Rules

| Field | dry_run | live |
|-------|---------|------|
| `polymarket_api_key` | MAY be empty | MUST NOT be empty |
| `polymarket_secret` | MAY be empty | MUST NOT be empty |
| `polymarket_passphrase` | MAY be empty | MUST NOT be empty |
| `polymarket_ws_url` | MUST be valid URL | MUST be valid URL |
| `polymarket_rest_url` | MUST be valid URL | MUST be valid URL |
| `active_markets` | MAY be empty | MUST have ≥ 1 market ID |

### Helper Method

```python
def get_active_market_ids(self) -> list[str]:
    """Parse active_markets into list of Condition IDs.

    Returns:
        list[str]: Stripped, non-empty market IDs. Empty list if active_markets is "".
    """
    if not self.active_markets:
        return []
    return [m.strip() for m in self.active_markets.split(",") if m.strip()]
```

### Security

- Secrets (`polymarket_api_key`, `polymarket_secret`, `polymarket_passphrase`) MUST NOT appear in logs, status output, or error messages.
- `status` command MUST NOT display secret values.
- `.env.production` MUST be in `.gitignore`.

### Scenarios

#### Scenario: default settings allow dry_run without secrets

- GIVEN no environment variables set
- WHEN `Settings()` is constructed
- THEN `polymarket_api_key=""`, `polymarket_ws_url="wss://..."`, `active_markets=""`

#### Scenario: get_active_market_ids parses comma-separated list

- GIVEN `active_markets="0xabc, 0xdef, 0xghi"`
- WHEN `get_active_market_ids()` is called
- THEN returns `["0xabc", "0xdef", "0xghi"]`

#### Scenario: get_active_market_ids handles empty string

- GIVEN `active_markets=""`
- WHEN `get_active_market_ids()` is called
- THEN returns `[]`

#### Scenario: status command does not leak secrets

- GIVEN settings with `polymarket_api_key="secret123"`
- WHEN `trady-ai status` is executed
- THEN output does NOT contain "secret123"

---

## Module 6: `src/trady_ai/config/runtime_config.py` — New Fields

**Purpose**: Add execution mode and order type configuration.

### New Fields

```python
from typing import Literal

class RuntimeConfig(BaseModel):
    # ... existing fields unchanged ...

    # Execution mode
    execution_mode: Literal["dry_run", "live"] = "dry_run"

    # Order defaults
    default_order_type: Literal["GTC"] = "GTC"
```

### Validation

- `execution_mode` MUST be "dry_run" or "live".
- `default_order_type` MUST be "GTC" (only supported type in Fase 2).
- Frozen: immutable post-creation.

### Scenarios

#### Scenario: default execution_mode is dry_run

- GIVEN no overrides
- WHEN `RuntimeConfig()` is constructed
- THEN `execution_mode == "dry_run"`

#### Scenario: invalid execution_mode raises

- GIVEN `execution_mode="paper"`
- WHEN `RuntimeConfig(execution_mode="paper")` is called
- THEN raises `ValidationError`

---

## Module 7: CLI Updates — `src/trady_ai/cli/main.py`

### New Command: `trady-ai capture`

```python
@cli.command()
@click.option("--reset", is_flag=True, default=False,
              help="DROP event_store and recreate (dev only)")
@click.option("--markets", default=None,
              help="Override active_markets (comma-separated)")
def capture(reset: bool, markets: str | None) -> None:
    """Start WebSocket capture from Polymarket into event_store.

    Connects to Polymarket WS, captures events, persists to event_store.
    Runs until interrupted (Ctrl+C).

    --reset: DROP + recreate event_store before starting (dev only).
    --markets: Override active_markets from settings.
    """
    ...
```

### Modified Command: `trady-ai run`

```python
@cli.command()
@click.option("--market", required=True, help="Market ID or symbol")
@click.option("--since-seq", default=0, type=int,
              help="Start from event seq (0 = all)")
def run(market: str, since_seq: int) -> None:
    """Run execution engine consuming from event_store.

    Reads captured events from event_store and runs the deterministic
    pipeline (state → strategy → risk → execution).
    """
    ...
```

### Modified Command: `trady-ai status`

```python
# Add to existing status output:
#   Event Store: N events (max_seq: M)
#   Capture: running/stopped
#   Active markets: [...]
#   Execution mode: dry_run/live
```

### Scenarios

#### Scenario: capture starts WS and persists events

- GIVEN Polymarket WS is available, active_markets configured
- WHEN `trady-ai capture` is executed
- THEN connects to WS, events appear in event_store, runs until Ctrl+C

#### Scenario: capture --reset drops event_store first

- GIVEN environment = "development", event_store has 50 rows
- WHEN `trady-ai capture --reset` is executed
- THEN event_store is dropped and recreated (0 rows), then capture starts

#### Scenario: capture --reset fails in production

- GIVEN environment = "production"
- WHEN `trady-ai capture --reset` is executed
- THEN exits with error: "reset is only available in development"

#### Scenario: run consumes from event_store

- GIVEN event_store has 20 events for market "0xabc"
- WHEN `trady-ai run --market 0xabc` is executed
- THEN engine processes 20 events, outputs summary stats

#### Scenario: status shows event_store stats

- GIVEN event_store has 100 events, capture is running
- WHEN `trady-ai status` is executed
- THEN output includes: "Event Store: 100 events (max_seq: 100)", "Capture: running"

---

## Module 8: `pyproject.toml` — New Dependency

### Change

Add `websockets>=13.0` to dependencies:

```toml
dependencies = [
    "pydantic-settings>=2.0",
    "click>=8.0",
    "structlog>=24.0",
    "httpx>=0.27",
    "sqlite-utils>=3.36",
    "numpy>=1.26",
    "websockets>=13.0",  # NEW: WebSocket client for Polymarket
]
```

---

## Module 9: Security — Secrets Validation

**Purpose**: Conditional secret validation based on execution_mode.

### validate_secrets Function

```python
def validate_secrets(settings: Settings, execution_mode: str) -> None:
    """Validate Polymarket credentials based on execution mode.

    Args:
        settings: Settings instance.
        execution_mode: "dry_run" or "live".

    Raises:
        ValueError: If execution_mode == "live" and any secret is empty.

    In dry_run: secrets MAY be empty. No validation error.
    In live: ALL secrets MUST be non-empty.
    """
    if execution_mode == "dry_run":
        return

    missing = []
    if not settings.polymarket_api_key:
        missing.append("polymarket_api_key")
    if not settings.polymarket_secret:
        missing.append("polymarket_secret")
    if not settings.polymarket_passphrase:
        missing.append("polymarket_passphrase")
    if not settings.active_markets:
        missing.append("active_markets")

    if missing:
        raise ValueError(
            f"Live execution requires: {', '.join(missing)}. "
            f"Set via TRADY_AI_{{NAME}} env vars or .env file."
        )
```

### Integration Points

- `trady-ai capture` calls `validate_secrets` before connecting WS.
- `trady-ai run` calls `validate_secrets` before executing.
- `trady-ai backtest` does NOT call `validate_secrets` (CSV-only, no platform).

### Scenarios

#### Scenario: dry_run allows empty secrets

- GIVEN `execution_mode="dry_run"`, all secrets empty
- WHEN `validate_secrets(settings, "dry_run")` is called
- THEN no error raised

#### Scenario: live requires all secrets

- GIVEN `execution_mode="live"`, `polymarket_api_key=""`
- WHEN `validate_secrets(settings, "live")` is called
- THEN raises `ValueError("Live execution requires: polymarket_api_key...")`

#### Scenario: live with all secrets set passes

- GIVEN `execution_mode="live"`, all secrets non-empty, active_markets configured
- WHEN `validate_secrets(settings, "live")` is called
- THEN no error raised

---

## File Structure

```
src/trady_ai/
├── adapters/
│   ├── __init__.py              # NEW
│   └── polymarket.py            # NEW: PolymarketAdapter + EventCapture
├── config/
│   ├── settings.py              # MODIFIED: +Polymarket fields, get_active_market_ids
│   └── runtime_config.py        # MODIFIED: +execution_mode, default_order_type
├── core/
│   ├── engine.py                # MODIFIED: +run_from_store()
│   ├── persistence.py           # MODIFIED: +event_store table, +5 functions
│   └── ...                      # Unchanged
├── cli/
│   └── main.py                  # MODIFIED: +capture, modified run/status
└── db/
    └── database.py              # Unchanged
```

---

## Dependency Graph

```
adapters/polymarket.py
  ├── PolymarketAdapter (stateless)
  │     ├── httpx (REST)
  │     ├── websockets (WS)
  │     └── core.models (MarketInput, Trade)
  │
  └── EventCapture (stateful)
        ├── PolymarketAdapter
        ├── core.persistence (append_event, get_max_seq, reset_event_store)
        └── threading

core/persistence.py
  ├── init_event_store (called from init_core_tables)
  ├── append_event → event_store INSERT OR IGNORE
  ├── get_events → event_store SELECT → MarketInput list
  ├── get_max_seq → SELECT MAX(seq)
  ├── count_events → SELECT COUNT(*)
  └── reset_event_store → DROP + CREATE

core/engine.py
  ├── run_from_store → get_events → self.run()
  └── (existing pipeline unchanged)

cli/main.py
  ├── capture → EventCapture.start()
  ├── run → Engine.run_from_store()
  └── status → event_store stats + capture state
```

---

## Testing Strategy

### Unit Tests

| Test | Module | Description |
|------|--------|-------------|
| `test_adapter_market_to_input` | PolymarketAdapter | Correct mapping from raw dict → MarketInput |
| `test_adapter_market_to_input_missing_keys` | PolymarketAdapter | KeyError on missing required keys |
| `test_adapter_order_to_trade` | PolymarketAdapter | Correct mapping from order response → Trade |
| `test_adapter_place_order_validation` | PolymarketAdapter | ValueError on invalid side/price/size |
| `test_adapter_subscribe_empty_markets` | PolymarketAdapter | ValueError on empty market_ids |
| `test_capture_insert_new` | EventCapture | _capture_one returns seq for new event |
| `test_capture_dedup` | EventCapture | _capture_one returns None for duplicate event_id |
| `test_capture_start_stop` | EventCapture | Thread lifecycle: start → is_running → stop |
| `test_capture_start_twice` | EventCapture | RuntimeError on double start |
| `test_capture_reset_dev` | EventCapture | reset() works in development |
| `test_capture_reset_prod` | EventCapture | RuntimeError in production |
| `test_persistence_append_event` | persistence | append_event returns seq |
| `test_persistence_append_dedup` | persistence | Duplicate event_id → returns None |
| `test_persistence_get_events` | persistence | get_events returns MarketInput list, ordered |
| `test_persistence_get_events_empty` | persistence | Empty store → empty list |
| `test_persistence_get_max_seq` | persistence | MAX(seq) or 0 if empty |
| `test_persistence_count_events` | persistence | COUNT(*) correct |
| `test_persistence_reset_event_store` | persistence | DROP + recreate, 0 rows |
| `test_persistence_init_idempotent` | persistence | init_event_store twice → no error |
| `test_settings_polymarket_defaults` | Settings | Default values correct |
| `test_settings_get_active_market_ids` | Settings | Comma-separated parsing |
| `test_settings_get_active_market_ids_empty` | Settings | Empty string → [] |
| `test_runtime_config_execution_mode` | RuntimeConfig | Default "dry_run" |
| `test_runtime_config_invalid_mode` | RuntimeConfig | ValidationError on invalid mode |
| `test_validate_secrets_dry_run` | security | Empty secrets OK in dry_run |
| `test_validate_secrets_live_missing` | security | ValueError in live with missing secrets |
| `test_validate_secrets_live_complete` | security | No error when all secrets present |
| `test_engine_run_from_store` | engine | Consumes from event_store correctly |
| `test_engine_run_from_store_since_seq` | engine | since_seq filters correctly |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_capture_to_store_pipeline` | WS mock → EventCapture → event_store → run_from_store → ExecutionResult |
| `test_dedup_integration` | Same event_id sent twice → only 1 row in event_store |
| `test_replay_from_event_store` | Same event_store → replay produces same outputs |
| `test_reconnect_gap_fill` | WS disconnect → REST gap fill → events continuous |
| `test_capture_cli_integration` | CliRunner: capture command starts and captures events |
| `test_run_cli_from_store` | CliRunner: run command processes event_store |

### Determinism Tests

| Test | Description |
|------|-------------|
| `test_event_store_determinism` | Same events inserted in same order → same seq assignment |
| `test_run_from_store_determinism` | Same event_store → run_from_store twice → identical ExecutionResult |

---

## Criterios de Aceptación

### Del Proposal (success criteria)

- [ ] Mismo evento → mismo registro en event_store (reproducible).
- [ ] Dedup: event_id duplicado → UNIQUE constraint lo rechaza, retorna None.
- [ ] WS reconexión: REST gap fill desde último timestamp en event_store.
- [ ] dry_run: pipeline corre sin firmar, secrets pueden estar vacíos.
- [ ] N mercados configurables sin tocar código (via `active_markets` setting).

### De la Spec (requisitos adicionales)

- [ ] PolymarketAdapter es 100% stateless — sin atributos de estado mutable.
- [ ] EventCapture aísla async (WS thread) del core sync.
- [ ] event_store es append-only — no UPDATE, solo INSERT OR IGNORE.
- [ ] `run_from_store` delegates to `run()` — core pipeline NO cambia.
- [ ] Core module NO importa de adapters — isolation boundary preserved (RFC-002).
- [ ] `validate_secrets` solo se invoca cuando execution_mode == "live".
- [ ] Secrets nunca aparecen en logs, status output, o error messages.
- [ ] `websockets>=13.0` agregado a pyproject.toml.
- [ ] CLI `capture` command starts WS, persists to event_store.
- [ ] CLI `capture --reset` drops event_store (dev only).
- [ ] CLI `run --market X` consumes from event_store.
- [ ] CLI `status` shows event_store stats + capture state.
- [ ] Todos los tests unitarios pasan (mínimo 29 tests nuevos).
- [ ] Todos los tests de integración pasan (mínimo 6 tests nuevos).
- [ ] `ruff check .` sin errores.
- [ ] `mypy src/` sin errores en código nuevo.

### Invariantes Arquitectónicos (RFC-002, RFC-000)

- [ ] Adapters traducen estructura, NUNCA poseen significado.
- [ ] Core NO depende de adapters — dependencia invertida via persistence.
- [ ] No hidden retries en adapter — fail-fast propagated.
- [ ] No silent normalization — adapter maps structure, not semantics.
- [ ] Async aislado en infrastructure boundary (WS thread).
- [ ] Core pipeline remains 100% sync and deterministic.
- [ ] Secrets governance: no leakage to logs/prompts/observability.
- [ ] Blast radius: adapter failure does not corrupt core tables.
- [ ] Rollback: eliminar adapters/ + revertir persistence/settings/pyproject.

### Iteration Plan

| Iteration | Scope | Key Deliverable |
|-----------|-------|-----------------|
| **1: dry_run** | Adapter + EventCapture + event_store + CLI capture/run | Pipeline corre sin firmar. WS capture funciona. Replay verified. |
| **2: live** | validate_secrets + place_order/cancel_order + credentials | Órdenes GTC Limit reales en Polymarket. Same architecture, secrets validated. |
