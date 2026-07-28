# Proposal: Bybit Spot Adapter

## Intent

Add a Bybit WebSocket adapter mirroring BinanceAdapter's contract. Binance testnet is geofenced from AWS Singapore — Bybit testnet is confirmed working from the VPS (52.220.172.112). Same `MarketInput` contract, ~80% code reuse, zero core changes.

**RFC**: RFC-002 (Platform Integration Architecture)
**Phase**: 5 — Platform Expansion

## Scope

### In Scope
- `src/trady_ai/adapters/bybit.py` — WebSocket trade stream + `market_to_input()`
- Config: `BYBIT_WS_URL`, `BYBIT_REST_URL` in `Settings`, reuse `TRADY_AI_ACTIVE_SYMBOLS`
- CLI: `--domain BYBIT-SPOT` support
- Guard script: add `BYBIT-SPOT` to `_VALID_DOMAINS`, static domain branch
- Tests: adapter unit tests + WS mock tests

### Out of Scope
- Order execution (paper trading only — dry_run mode)
- Multiple exchanges simultaneously (one domain per session)

## Capabilities

### New Capabilities
- `bybit-adapter`: Stateless WebSocket adapter translating Bybit trade streams
  (`wss://stream-testnet.bybit.com/v5/public/spot`) into `MarketInput`. Subscription-based
  (`{"op": "subscribe", "args": ["publicTrade.BTCUSDT"]}`), trades in `data[]` arrays.

### Modified Capabilities
- `static-domain`: Add `BYBIT-SPOT` to `_VALID_DOMAINS` and static validation branch
- `cli-domain`: Accept `--domain BYBIT-SPOT`, wire `BybitAdapter` per settings
- `binance-config`: Add `bybit_ws_url`, `bybit_rest_url` fields (platform co-location)

## Approach

Same adapter contract as `BinanceAdapter`:
1. `subscribe_websocket(symbols) → Generator[dict]` — subscription-based WS
2. `market_to_input(raw) → MarketInput` — 1:1 field mapping

Field mapping (`T`→timestamp, `s`→market_id, `p`→price, `v`→volume, source=`"bybit"`).
Key difference: trades arrive batched in `data[]` arrays — adapter iterates and yields
each trade individually.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/trady_ai/adapters/bybit.py` | New | BybitAdapter (~250 LOC) |
| `src/trady_ai/config/settings.py` | Modified | +2 fields (`bybit_ws_url`, `bybit_rest_url`) |
| `.env.example` | Modified | +Bybit config section |
| `src/trady_ai/cli/main.py` | Modified | +`--domain BYBIT-SPOT` |
| `scripts/ensure_active_market.py` | Modified | +`BYBIT-SPOT` to `_VALID_DOMAINS`, static branch |
| `tests/adapters/test_bybit.py` | New | WebSocket mock + unit tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| WS format divergence (data arrays vs singles) | Low | Bybit API v5 docs confirmed; batch iteration is trivial |
| Testnet stability vs production | Low | Same testnet tier as Binance; VPS confirmed working |
| Bybit deprecation of v5 public WS | Low | v5 is current; fallback to REST polling if needed |

## Rollback Plan

Delete `src/trady_ai/adapters/bybit.py`, revert `settings.py` Bybit fields,
remove `BYBIT-SPOT` from CLI/guard. Zero core impact — adapter is additive.

## Dependencies

- `websockets>=13.0` (already in pyproject.toml)
- Bybit testnet endpoints confirmed reachable from AWS Singapore

## Success Criteria

- [ ] `BybitAdapter.market_to_input()` maps `{T, s, p, v}` → valid `MarketInput`
- [ ] `subscribe_websocket(["BTCUSDT"])` yields parsed trade events from testnet
- [ ] Existing tests pass unchanged (adapter is additive)
- [ ] Dry-run session captures real-time trades from `wss://stream-testnet.bybit.com`
