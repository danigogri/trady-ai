# Binance Adapter Specification

## Purpose

Stateless WebSocket adapter translating Binance testnet trade streams into the
existing deterministic pipeline via `MarketInput`. Pure 1:1 field mapping — no
book normalization, no invented volume. Implements the same contract as
`PolymarketAdapter`: `subscribe_websocket(symbols)` → `Generator[dict]` and
`trade_to_input(raw)` → `MarketInput`.

*Ref: proposal §Capabilities — binance-adapter (new)*

## Requirements

| Req | Title | Strength | Summary |
|-----|-------|----------|---------|
| REQ-BA-001 | Constructor | MUST | Accept `ws_url` and `rest_url` strings |
| REQ-BA-002 | WebSocket Subscribe | MUST | Connect to testnet WS, subscribe to `<symbol>@trade` streams, yield parsed trade events |
| REQ-BA-003 | Trade to MarketInput | MUST | Map `E`→timestamp, `s`→market_id, `p`→price, `q`→volume, source=`"binance"` |
| REQ-BA-004 | Adapter Contract | MUST | Implement `subscribe_websocket(symbols)` → `Generator[dict]` and `trade_to_input(raw)` → `MarketInput` |
| REQ-BA-005 | Error Handling | MUST | Gracefully handle non-JSON messages, connection failures, and WS disconnects |
| REQ-BA-006 | Deterministic Mapping | SHALL | Same raw trade event → same `MarketInput` always |

### REQ-BA-001: Constructor

The `BinanceAdapter(ws_url, rest_url)` constructor SHALL accept exactly two
positional string arguments: the WebSocket endpoint URL and the REST base URL.
No authentication parameters are required (testnet is unauthenticated).

#### Scenario: Valid construction

- GIVEN `ws_url = "wss://testnet.binance.vision/ws"` and `rest_url = "https://testnet.binance.vision"`
- WHEN `BinanceAdapter(ws_url, rest_url)` is instantiated
- THEN the adapter stores both URLs and is ready for use

### REQ-BA-002: WebSocket Subscribe

`subscribe_websocket(symbols: list[str])` SHALL connect to the configured WS
endpoint, send a subscription message for each symbol's `<symbol>@trade` stream,
and yield parsed JSON trade events as dicts.

#### Scenario: Single symbol happy path

- GIVEN a `BinanceAdapter` connected to `wss://testnet.binance.vision/ws`
- WHEN `subscribe_websocket(["btcusdt"])` is called
- THEN a combined stream message `{"method": "SUBSCRIBE", "params": ["btcusdt@trade"], "id": 1}` is sent
- AND each received trade event dict is yielded as it arrives

#### Scenario: Multi-symbol subscription

- GIVEN symbols `["btcusdt", "ethusdt"]`
- WHEN `subscribe_websocket(["btcusdt", "ethusdt"])` is called
- THEN a single subscribe message with `params: ["btcusdt@trade", "ethusdt@trade"]` is sent
- AND trade events for both symbols are yielded

#### Scenario: Empty symbol list

- GIVEN an empty list `[]`
- WHEN `subscribe_websocket([])` is called
- THEN a `ValueError` is raised with a message indicating symbols must not be empty

#### Scenario: Connection failure

- GIVEN an unreachable WS URL
- WHEN `subscribe_websocket(["btcusdt"])` is called
- THEN a `ConnectionError` is raised (or propagated from the websocket library)

#### Scenario: Graceful disconnect

- GIVEN an active WS connection receiving trades
- WHEN the connection is closed by the server or caller stops iterating
- THEN the generator stops cleanly without unhandled exceptions

### REQ-BA-003: Trade to MarketInput

`trade_to_input(raw: dict)` SHALL map Binance trade event fields to a
`MarketInput` model. The mapping is:

| Field | Binance Key | Type | Transformation |
|-------|------------|------|----------------|
| timestamp | `E` | int (epoch ms) | `datetime.fromtimestamp(E / 1000, tz=UTC)` |
| market_id | `s` | str | `.lower()` |
| price | `p` | str | `Decimal(p)` |
| volume | `q` | str | `Decimal(q)` |
| source | (static) | — | `"binance"` |

#### Scenario: Valid trade event

- GIVEN `raw = {"e": "trade", "E": 1752000000000, "s": "BTCUSDT", "p": "98765.43", "q": "0.00123"}`
- WHEN `adapter.trade_to_input(raw)` is called
- THEN returns `MarketInput(timestamp=datetime(2025, 7, 8, ..., tzinfo=UTC), market_id="btcusdt", price=Decimal("98765.43"), volume=Decimal("0.00123"), source="binance")`

#### Scenario: Missing required field

- GIVEN `raw = {"e": "trade", "s": "BTCUSDT", "p": "50000"}` (missing `E` and `q`)
- WHEN `adapter.trade_to_input(raw)` is called
- THEN a `KeyError` is raised for the missing required field

#### Scenario: Invalid numeric value

- GIVEN `raw = {"e": "trade", "E": 1752000000000, "s": "BTCUSDT", "p": "not_a_number", "q": "0.001"}`
- WHEN `adapter.trade_to_input(raw)` is called
- THEN a `ValueError` (or `DecimalException`) is raised

### REQ-BA-004: Adapter Contract Compatibility

`BinanceAdapter` SHALL expose the same two-method interface that `EventCapture`
depends on, making it a drop-in replacement for `PolymarketAdapter` when wired
through the paper trading session.

#### Scenario: Drop-in compatibility

- GIVEN a `PaperTradingSession` wired with `BinanceAdapter` instead of `PolymarketAdapter`
- WHEN `run_session()` is called with symbols instead of market IDs
- THEN `EventCapture` uses `adapter.subscribe_websocket()` and `adapter.trade_to_input()` without modification

### REQ-BA-005: Error Handling

The adapter SHALL handle non-JSON WebSocket messages gracefully, log warnings,
and continue streaming. Connection failures SHALL propagate as exceptions.
The adapter itself does NOT implement reconnection — `EventCapture` handles that
via its existing exponential-backoff logic.

#### Scenario: Non-JSON message

- GIVEN the WS connection receives a non-JSON payload (e.g., plain text ping)
- WHEN the adapter attempts to parse it
- THEN the message is logged as a warning and skipped (not yielded)

#### Scenario: Server-initiated close

- GIVEN the WS server sends a close frame mid-stream
- WHEN the adapter's WS read loop detects the close
- THEN the generator exits cleanly (stops iteration)

### REQ-BA-006: Deterministic Mapping

`trade_to_input()` is a pure function. Same input SHALL produce the same output
every time. No external state, no randomness, no time-of-day effects.

#### Scenario: Idempotent mapping

- GIVEN the same Binance trade event dict
- WHEN `trade_to_input(raw)` is called twice
- THEN both `MarketInput` instances are equal (`==`)

---

**Boundary**: This adapter translates structure, NEVER owns meaning (RFC-002).
It does not normalize prices, calculate derived metrics, or make trading decisions.
All decisions belong to `MarkovStrategy` and `ExecutionEngine` in the Core layer.
