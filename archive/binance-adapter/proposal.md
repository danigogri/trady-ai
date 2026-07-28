# Proposal: Binance Spot Adapter

## Intent

Add a Binance WebSocket adapter that feeds tick-by-tick trade streams into the existing
deterministic pipeline. Polymarket is event-prediction-only (airdrops, IPOs); Binance provides
continuous price trades — the correct data shape for Markov transition detection. Same
`MarketInput` contract, zero core changes.

**RFC**: RFC-002 (Platform Integration Architecture)
**Phase**: Fase 5 (Platform Expansion)

## Scope

### In Scope
- `src/trady_ai/adapters/binance.py`: BinanceAdapter with REST + WebSocket trade stream
- Config: Binance settings in `config/settings.py` + `.env.example`
- CLI: `--domain BINANCE-SPOT` support
- Guard script: static domain mode (symbols configured, not discovered)
- Tests: adapter unit tests + WebSocket mock tests

### Out of Scope
- Order execution (paper trading only — dry_run mode)
- Multiple exchange support (V1 = Binance only)
- Futures/derivatives (spot only)

## Capabilities

### New Capabilities
- `binance-adapter`: Stateless WebSocket adapter translating Binance trade streams
  (`wss://testnet.binance.vision/ws/<symbol>@trade`) into `MarketInput`. Pure 1:1 field
  mapping — no normalization layer needed (unlike Polymarket's book-snapshot conversion).

### Modified Capabilities
None. `EventCapture`, `ExecutionEngine`, `MarkovEngine`, and `CalibrationFramework` are
unchanged. The adapter is additive.

## Approach

`EventCapture` is platform-agnostic — it depends on:
1. `adapter.subscribe_websocket(symbols) → Generator[dict]`
2. `adapter.trade_to_input(raw) → MarketInput`

`BinanceAdapter` implements the same contract. Each trade event maps directly:
`e: {E, s, p, q}` → `MarketInput(timestamp=E, market_id=s, price=p, volume=q, source="binance")`.
No book normalization, no invented volume.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/trady_ai/adapters/binance.py` | New | BinanceAdapter (~250 LOC) |
| `src/trady_ai/config/settings.py` | Modified | +2 fields (`binance_ws_url`, `binance_rest_url`) |
| `.env.example` | Modified | +Binance config section |
| `src/trady_ai/cli/main.py` | Modified | +`--domain BINANCE-SPOT` |
| `scripts/guard.py` | Modified | +static domain entry |
| `tests/adapters/test_binance.py` | New | WebSocket mock + unit tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Binance testnet instability | Medium | Production WS as documented fallback; single WS connection |
| Testnet rate limiting | Low | One WS connection per session — no concurrent streams |
| WS disconnection | Low | Reuse `EventCapture` reconnect logic (exponential backoff) |

## Rollback Plan

Delete `src/trady_ai/adapters/binance.py`, revert `settings.py` Binance fields,
remove `BINANCE-SPOT` from CLI/guard. Zero core impact — adapter is additive and
core never references it.

## Dependencies

- `websockets>=13.0` (already in pyproject.toml)

## Success Criteria

- [ ] `BinanceAdapter.trade_to_input()` produces valid `MarketInput` from testnet trade JSON
- [ ] Existing 199 tests pass unchanged (adapter is additive)
- [ ] Dry-run session captures real-time trades from `wss://testnet.binance.vision`
- [ ] Calibration framework processes Binance-origin MarketInput identically to CSV/Polymarket
