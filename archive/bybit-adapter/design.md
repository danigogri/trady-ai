# Design: Bybit Spot Adapter

## Technical Approach

Add a `BybitAdapter` mirroring `BinanceAdapter`'s contract (`subscribe_websocket` →
`Generator[dict]`, `market_to_input` → `MarketInput`). The only structural differences
are Bybit's subscription model (JSON `op: subscribe` vs Binance's URL-encoded streams)
and batch `data[]` arrays. All else is 1:1 field mapping with no core changes.

Ref specs: **bybit-adapter** (REQ-BB-001–007), **bybit-config** (REQ-BYC-001–006),
**domain-routing** (REQ-CLI-001–004, REQ-SD-001, REQ-SD-005).

## Architecture Decisions

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Mirror BinanceAdapter class-for-class | Duplicates ~140 LOC of WS event-loop boilerplate | **Chosen** — adapters are independent boundary objects per RFC-002; shared abstraction comes later |
| Extract `EventCapture`-style reconnect logic | Adds tight coupling to Polymarket's capture thread model | **Rejected** — adapter must be stateless; reconnect belongs to `EventCapture`, which is Polymarket-only |
| Iterate `data[]` inside `subscribe_websocket` | Yields one dict per trade, consumer-agnostic | **Chosen** — matches REQ-BB-004 batch iteration contract |

## Data Flow

```
Bybit WS                       BybitAdapter                        Core Pipeline
────────                       ────────────                        ─────────────
JSON msg                       subscribe_websocket()
{ "topic": "publicTrade.       │
  BTCUSDT",                    │ yields one dict per trade
  "data": [                    │
    { T:1752..., s:"BTCUSDT",  ├─→ market_to_input(raw) ──→ MarketInput
      p:"98765", v:"0.001" },  │       (pure function)
    { T:1752..., s:"BTCUSDT",  │
      p:"98766", v:"0.002" }   │
  ]                            │
}                              │
```

## File Manifest

| File | Action | Description |
|------|--------|-------------|
| `src/trady_ai/adapters/bybit.py` | **Create** | `BybitAdapter` (~180 LOC, REQ-BB-001–007) |
| `src/trady_ai/config/settings.py` | Modify | +`bybit_ws_url`, `bybit_rest_url` fields (REQ-BYC-005) |
| `.env.example` | Modify | +Bybit Connection section (REQ-BYC-006) |
| `src/trady_ai/cli/main.py` | Modify | `_VALID_DOMAIN_SET` + `BYBIT-SPOT` branch (REQ-CLI-001–004) |
| `scripts/ensure_active_market.py` | Modify | `_VALID_DOMAINS` + `elif domain == "BYBIT-SPOT"` → `_static_domain_pass()` (REQ-SD-001, REQ-SD-005) |
| `tests/adapters/test_bybit.py` | **Create** | Unit + WS mock tests |

## Interfaces / Contracts

`BybitAdapter` implements the same protocol as `BinanceAdapter`:

```python
class BybitAdapter:
    def __init__(self, ws_url: str, rest_url: str): ...
    def subscribe_websocket(self, symbols: list[str]) -> Generator[dict, None, None]: ...
    @staticmethod
    def market_to_input(raw: dict) -> MarketInput: ...
```

Key Bybit-specific differences:
- **WS subscribe**: `{"op": "subscribe", "args": ["publicTrade.BTCUSDT"]}` (JSON, not URL streams)
- **Symbol case**: UPPERCASE for topics (`publicTrade.BTCUSDT`), uppercase preserved in `market_id`
- **Batch**: iterate `msg["data"]`, yield each element individually
- **Fields**: `T`→timestamp (epoch ms / 1000), `s`→market_id, `p`→price (Decimal), `v`→volume (Decimal), source=`"bybit"`

CLI wiring (pattern matches Binance branch in `main.py:442–457`):
```python
elif domain == "BYBIT-SPOT":
    from trady_ai.adapters.bybit import BybitAdapter
    symbols = list(markets) if markets else settings.get_active_symbols()
    adapter = BybitAdapter(ws_url=settings.bybit_ws_url, rest_url=settings.bybit_rest_url)
    market_ids = list(symbols)  # UPPERCASE, no .lower()
```

Guard routing (adds to existing `main()` in `ensure_active_market.py:535`):
```python
elif domain == "BYBIT-SPOT":
    return _static_domain_pass(env)
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `market_to_input()` pure function | Fixed dicts → assert `MarketInput` fields (REQ-BB-003, REQ-BB-007) |
| Unit | `subscribe_websocket` batch iteration | Mock WebSocket, send multi-trade `data[]`, assert yielded count (REQ-BB-004) |
| Unit | Error handling | Non-JSON, missing fields, empty symbols, invalid numerics (REQ-BB-006) |
| Integration | CLI `--domain BYBIT-SPOT` | CLI test: valid domain accepted, adapter instantiated (REQ-CLI-001, REQ-CLI-002) |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The adapter only opens outbound WebSocket connections and maps JSON fields; all actions belong to existing `PaperTradingSession` (dry-run only).

## Migration / Rollout

No migration required. `BybitAdapter` is additive. Existing `.env` files without Bybit vars fall back
to documented defaults. Rollback: delete `bybit.py`, revert 4 modified files.

## Open Questions

None.
