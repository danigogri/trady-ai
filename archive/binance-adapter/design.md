# Design: Binance Spot Adapter

## Technical Approach

Add a stateless `BinanceAdapter` implementing the same contract as `PolymarketAdapter`:
`subscribe_websocket(symbols)` → `Generator[dict]` and `market_to_input(raw)` → `MarketInput`.
The adapter translates Binance testnet WebSocket trade streams (1:1 field mapping) into the
existing deterministic pipeline. Zero core changes — the `PaperTradingSession` receives whichever
adapter the CLI provides. Wire via domain-to-adapter factory in the CLI `session` command.

**Ref specs**: `binance-adapter`, `binance-config`, `static-domain`, `cli-domain`.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Adapter method name | `market_to_input` | `trade_to_input` | `EventCapture._capture_one` calls `adapter.market_to_input(raw)`. Changing the method name would require modifying `EventCapture`, violating the "no core changes" constraint. Internal mapping logic is Binance-specific; the contract name follows the existing interface. |
| WS endpoint | Use `ws_url` directly | Concatenate `/ws` suffix | Spec REQ-BC-001 default is already `wss://testnet.binance.vision/ws`. No path assembly needed. |
| Subscription mode | Combined streams (single WS connection, `SUBSCRIBE` message) | Individual per-symbol connections | Simpler, lower connection count, matches spec REQ-BA-002 scenario. |
| Async bridge | Copy `PolymarketAdapter` pattern (internal asyncio loop → sync Generator) | Rewrite as async-only | Preserves sync `EventCapture` contract. `websockets` library already works this way in `PolymarketAdapter`. |
| Source field in EventCapture | No change to `EventCapture` | Parameterize `source` | `PaperTradingSession` handles `market_to_input` calls; `EventCapture._capture_one` hardcodes `source="polymarket"` but the BinanceAdapter is wired via `PaperTradingSession`, not the standalone `EventCapture`. If future `PaperTradingSession` reuses `EventCapture`, the source parameterization is a separate concern outside this change scope. |

## Data Flow

```
Binance WS (testnet.binance.vision)
  │  {"e":"trade","E":...,"s":"BTCUSDT","p":"...","q":"..."}
  ▼
BinanceAdapter.subscribe_websocket(["btcusdt","ethusdt"])
  │  yield parsed dict
  ▼
BinanceAdapter.market_to_input(raw)
  │  MarketInput(timestamp=..., market_id="btcusdt", price=Decimal(...), volume=Decimal(...), source="binance")
  ▼
PaperTradingSession
  │  calls adapter.subscribe_websocket(), adapter.market_to_input()
  ▼
EventCapture (unchanged) ──→ event_store (SQLite)
  │
  ▼
ExecutionEngine ──→ MarkovEngine ──→ signals
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/trady_ai/adapters/binance.py` | **Create** | `BinanceAdapter` class (~100 LOC). Constructor stores `ws_url`/`rest_url`. `subscribe_websocket()` opens WS, sends `{"method":"SUBSCRIBE","params":["<symbol>@trade",...],"id":1}`, yields parsed dicts. `market_to_input()` static pure function: `E`→timestamp, `s`→market_id (lowercase), `p`→price, `q`→volume, source=`"binance"`. |
| `src/trady_ai/config/settings.py` | **Modify** | Add three fields: `binance_ws_url: str` (default `wss://testnet.binance.vision/ws`), `binance_rest_url: str` (default `https://testnet.binance.vision`), `active_symbols: str` (default `""`). Add `get_active_symbols() → list[str]`: split + strip + filter empty. All fields frozen via `model_config.frozen=True`. |
| `.env.example` | **Modify** | Add `# ── Binance Connection ──` section with `TRADY_AI_BINANCE_WS_URL`, `TRADY_AI_BINANCE_REST_URL`, `TRADY_AI_ACTIVE_SYMBOLS`. Update domain section to document `BINANCE-SPOT`. |
| `src/trady_ai/cli/main.py` | **Modify** | In `session()`: validate domain against `{"FOOTBALL-WINNER","CRYPTO-BINARY","BINANCE-SPOT"}`. Build adapter: `PolymarketAdapter(...)` for existing domains, `BinanceAdapter(ws_url=settings.binance_ws_url, rest_url=settings.binance_rest_url)` for `BINANCE-SPOT`. Pass lowercase symbols from `settings.get_active_symbols()`. |
| `scripts/ensure_active_market.py` | **Modify** | Add `"BINANCE-SPOT"` to `_VALID_DOMAINS`. In `_load_discovery_config`: accept `BINANCE-SPOT` without requiring tag_slug/leagues. In `main()`: add early `if domain == "BINANCE-SPOT": return _static_domain_pass(env)` branch. Add `_static_domain_pass(env)` function: read `TRADY_AI_ACTIVE_SYMBOLS`, validate uppercase alphanumeric+comma format, exit 0 if valid, exit 1 if empty/invalid. No HTTP calls, no `.env` writes. |
| `tests/adapters/test_binance.py` | **Create** | Unit tests: `trade_to_input` valid/missing/invalid, constructor, empty symbols raises ValueError. Integration: mock WebSocket with `AsyncMock` for subscribe + message yield. |

## Interfaces / Contracts

```python
# src/trady_ai/adapters/binance.py

class BinanceAdapter:
    def __init__(self, ws_url: str, rest_url: str): ...
    def subscribe_websocket(self, symbols: list[str]) -> Generator[dict, None, None]: ...
    @staticmethod
    def market_to_input(raw: dict) -> MarketInput: ...

# settings.py additions
class Settings(BaseSettings):
    binance_ws_url: str = "wss://testnet.binance.vision/ws"
    binance_rest_url: str = "https://testnet.binance.vision"
    active_symbols: str = ""

    def get_active_symbols(self) -> list[str]:
        if not self.active_symbols:
            return []
        return [s.strip() for s in self.active_symbols.split(",") if s.strip()]
```

`market_to_input` field mapping:

| Binance Key | MarketInput Field | Transform |
|------------|-------------------|-----------|
| `E` (int, epoch ms) | `timestamp` | `datetime.fromtimestamp(E/1000, tz=UTC)` |
| `s` (str) | `market_id` | `.lower()` |
| `p` (str) | `price` | `Decimal(p)` |
| `q` (str) | `volume` | `Decimal(q)` |
| (static) | `source` | `"binance"` |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `market_to_input` valid/missing/invalid fields, empty symbols raises `ValueError` | Parametrized pytest, pure-function tests |
| Unit | `get_active_symbols` parsing (comma, whitespace, empty) | Parametrized pytest |
| Integration | `subscribe_websocket` WS mock — connect, subscribe, receive trade event | `AsyncMock` wrapping `websockets.connect`, assert subscribe message and yielded dict |
| Integration | Guard `_static_domain_pass` valid/invalid/empty symbols | Call function with mock env, assert exit code |
| Regression | Existing 199 tests pass unchanged | `pytest` full suite |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The change is a pure WebSocket data adapter with static config and CLI flag addition. No risk surface beyond existing `websockets` dependency behavior.

## Migration / Rollout

No migration required. Feature is additive — existing Polymarket workflows unchanged. Rollback: delete `binance.py`, revert settings/CLI/guard/`.env.example` changes. Zero core impact.

## Open Questions

- [ ] `PaperTradingSession` is referenced in `main.py` but not yet implemented — if it reuses `EventCapture` internally, `source="polymarket"` hardcoding in `EventCapture._capture_one` must be parameterized (separate concern, outside this change scope).
