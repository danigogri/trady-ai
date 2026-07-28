# Bybit Adapter Specification

## Purpose

Stateless WebSocket adapter translating Bybit testnet trade streams into the
existing deterministic pipeline via `MarketInput`. Mirrors `BinanceAdapter`
contract with Bybit-specific subscription format and field mapping. Key
difference: trades arrive batched in `data[]` arrays — adapter yields each
individually.

*Ref: proposal §Capabilities — bybit-adapter (new)*

## Requirements

| Req | Title | Strength | Summary |
|-----|-------|----------|---------|
| REQ-BB-001 | Constructor | MUST | Accept `ws_url` and `rest_url` strings |
| REQ-BB-002 | WebSocket Subscribe | MUST | Connect to Bybit testnet WS, subscribe to `publicTrade.<SYMBOL>`, yield individual trades |
| REQ-BB-003 | Market to MarketInput | MUST | Map `T`→timestamp, `s`→market_id, `p`→price, `v`→volume, source=`"bybit"` |
| REQ-BB-004 | Batch Iteration | MUST | Iterate `data[]` arrays, yield one dict per trade |
| REQ-BB-005 | Adapter Contract | MUST | Implement `subscribe_websocket(symbols)` → `Generator[dict]` and `market_to_input(raw)` → `MarketInput` |
| REQ-BB-006 | Error Handling | MUST | Handle non-JSON messages, connection failures, WS disconnects gracefully |
| REQ-BB-007 | Deterministic Mapping | SHALL | Same raw trade event → same `MarketInput` always |

### REQ-BB-001: Constructor

`BybitAdapter(ws_url, rest_url)` SHALL accept two positional string arguments:
WebSocket endpoint and REST base URL. No authentication required (testnet is
unauthenticated).

#### Scenario: Valid construction

- GIVEN `ws_url = "wss://stream-testnet.bybit.com/v5/public/spot"` and `rest_url = "https://api-testnet.bybit.com"`
- WHEN `BybitAdapter(ws_url, rest_url)` is instantiated
- THEN the adapter stores both URLs and is ready for use

### REQ-BB-002: WebSocket Subscribe

`subscribe_websocket(symbols: list[str])` SHALL connect to the Bybit WS endpoint,
send `{"op": "subscribe", "args": ["publicTrade.<SYMBOL>", ...]}`, and yield
parsed JSON trade events. Each message contains a `data[]` array — see REQ-BB-004
for batch handling.

#### Scenario: Single symbol

- GIVEN `BybitAdapter` connected to `wss://stream-testnet.bybit.com/v5/public/spot`
- WHEN `subscribe_websocket(["BTCUSDT"])` is called
- THEN `{"op": "subscribe", "args": ["publicTrade.BTCUSDT"]}` is sent
- AND trade events are yielded as they arrive

#### Scenario: Multi-symbol subscription

- GIVEN symbols `["BTCUSDT", "ETHUSDT"]`
- WHEN `subscribe_websocket(["BTCUSDT", "ETHUSDT"])` is called
- THEN args are `["publicTrade.BTCUSDT", "publicTrade.ETHUSDT"]`

#### Scenario: Empty symbol list

- GIVEN `[]`
- WHEN `subscribe_websocket([])` is called
- THEN `ValueError` is raised

#### Scenario: Connection failure

- GIVEN unreachable WS URL
- WHEN `subscribe_websocket(["BTCUSDT"])` is called
- THEN `ConnectionError` propagates

#### Scenario: Graceful disconnect

- GIVEN active WS connection
- WHEN server closes or caller stops iterating
- THEN generator stops cleanly without unhandled exceptions

### REQ-BB-003: Market to MarketInput

`market_to_input(raw: dict)` SHALL map Bybit trade fields to `MarketInput`:

| Field | Bybit Key | Type | Transformation |
|-------|----------|------|----------------|
| timestamp | `T` | int (epoch ms) | `datetime.fromtimestamp(T / 1000, tz=UTC)` |
| market_id | `s` | str | `.upper()` |
| price | `p` | str | `Decimal(p)` |
| volume | `v` | str | `Decimal(v)` |
| source | (static) | — | `"bybit"` |

#### Scenario: Valid trade event

- GIVEN `raw = {"T": 1752000000000, "s": "BTCUSDT", "p": "98765.43", "v": "0.00123"}`
- WHEN `adapter.market_to_input(raw)` is called
- THEN returns `MarketInput(timestamp=datetime(2025, 7, 8, ..., tz=UTC), market_id="BTCUSDT", price=Decimal("98765.43"), volume=Decimal("0.00123"), source="bybit")`

#### Scenario: Missing required field

- GIVEN `raw = {"s": "BTCUSDT", "p": "50000"}` (missing `T` and `v`)
- WHEN `adapter.market_to_input(raw)` is called
- THEN `KeyError` is raised

#### Scenario: Invalid numeric value

- GIVEN `raw = {"T": 1752000000000, "s": "BTCUSDT", "p": "bad", "v": "0.001"}`
- WHEN `adapter.market_to_input(raw)` is called
- THEN `ValueError` or `DecimalException` is raised

### REQ-BB-004: Batch Iteration

Bybit WS messages deliver trades in `data[]` arrays (multiple trades per
message). The adapter SHALL iterate each array element and yield individual
trade dicts. Single-element arrays SHALL also be yielded individually.

#### Scenario: Multi-trade batch

- GIVEN WS message `{"topic": "publicTrade.BTCUSDT", "data": [{"T": 100, "s": "BTCUSDT", "p": "50000", "v": "0.1"}, {"T": 101, "s": "BTCUSDT", "p": "50001", "v": "0.2"}]}`
- WHEN processed by the adapter
- THEN two individual dicts are yielded sequentially

#### Scenario: Single-trade message

- GIVEN WS message with `data: [{"T": 100, "s": "BTCUSDT", "p": "50000", "v": "0.1"}]`
- WHEN processed
- THEN one dict is yielded

### REQ-BB-005: Adapter Contract Compatibility

`BybitAdapter` SHALL expose the same interface as `BinanceAdapter` and
`PolymarketAdapter`: `subscribe_websocket(symbols)` → `Generator[dict]` and
`market_to_input(raw)` → `MarketInput`.

#### Scenario: Drop-in compatibility

- GIVEN `PaperTradingSession` wired with `BybitAdapter`
- WHEN `run_session()` is called with `--domain BYBIT-SPOT`
- THEN `EventCapture` uses `adapter.subscribe_websocket()` and `adapter.market_to_input()` without modification

### REQ-BB-006: Error Handling

The adapter SHALL handle non-JSON WebSocket messages gracefully (log warning,
skip, continue). Connection failures SHALL propagate. No reconnection logic —
`EventCapture` handles exponential backoff.

#### Scenario: Non-JSON message

- GIVEN WS receives non-JSON payload (e.g., plain text ping)
- WHEN adapter attempts to parse it
- THEN logged as warning and skipped (not yielded)

#### Scenario: Server-initiated close

- GIVEN WS server sends close frame mid-stream
- WHEN read loop detects the close
- THEN generator exits cleanly

### REQ-BB-007: Deterministic Mapping

`market_to_input()` is a pure function. Same input SHALL produce the same output
every time. No external state, no randomness, no time-of-day effects.

#### Scenario: Idempotent mapping

- GIVEN the same Bybit trade event dict
- WHEN `market_to_input(raw)` is called twice
- THEN both `MarketInput` instances are equal (`==`)

---

**Boundary**: This adapter translates structure, NEVER owns meaning (RFC-002).
It does not normalize prices, calculate derived metrics, or make trading
decisions. All decisions belong to `MarkovStrategy` and `ExecutionEngine` in
the Core layer.
