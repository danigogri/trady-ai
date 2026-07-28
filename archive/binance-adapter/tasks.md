# Tasks: Binance Spot Adapter

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~355 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Delivery strategy | ask-always |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Adapter + config + guard + integration | PR 1 | `pytest tests/unit/test_binance_adapter.py -v` | `python -m trady_ai paper-trade session --domain BINANCE-SPOT` (dry-run, valid symbols in .env) | Delete `binance.py`, revert `settings.py`/`main.py`/`ensure_active_market.py`/`.env.example` — zero core impact |

## Phase 1: BinanceAdapter (core)

- [x] 1.1 RED: Create `tests/unit/test_binance_adapter.py` — `test_market_to_input_valid` (E→timestamp, s→lowercase, p/q→Decimal, source="binance"), `test_market_to_input_missing_key` (KeyError on absent E/q), `test_market_to_input_invalid_decimal` (ValueError on non-numeric p/q), `test_market_to_input_idempotent` (same input == same MarketInput)
- [x] 1.2 RED: Add to same test file — `test_constructor` (stores ws_url/rest_url), `test_subscribe_empty_symbols` (ValueError), `test_subscribe_ws_mock` (AsyncMock connect, assert SUBSCRIBE message `{"method":"SUBSCRIBE","params":["btcusdt@trade"],"id":1}`, yield parsed dict), `test_subscribe_multi_symbol` (params with multiple `@trade` streams), `test_subscribe_non_json_skip` (log warning, continue)
- [x] 1.3 GREEN: Create `src/trady_ai/adapters/binance.py` — `BinanceAdapter(ws_url, rest_url)` constructor; `market_to_input(raw)` static: E→`datetime.fromtimestamp(E/1000, UTC)`, s→`.lower()`, p/q→`Decimal`, source=`"binance"`
- [x] 1.4 GREEN: Implement `subscribe_websocket(symbols)` — `websockets.connect(ws_url)` via internal asyncio loop, send SUBSCRIBE `{"method":"SUBSCRIBE","params":[f"{s.lower()}@trade" for s in symbols],"id":1}`, yield parsed trade dicts, log+warn+skip non-JSON, clean exit on close frame
- [x] 1.5 GREEN: Run `pytest tests/unit/test_binance_adapter.py -v` — all 1.1–1.2 tests pass

## Phase 2: Configuration

- [x] 2.1 RED: Add `test_binance_settings` to existing `test_config.py` — default WS/REST URLs, explicit override, `get_active_symbols()` comma/whitespace/empty parsing, immutability guard
- [x] 2.2 GREEN: Add to `src/trady_ai/config/settings.py` — `binance_ws_url: str` (default `wss://testnet.binance.vision/ws`), `binance_rest_url: str` (default `https://testnet.binance.vision`), `active_symbols: str` (default `""`), `get_active_symbols() → list[str]`: split + strip + filter empty
- [x] 2.3 RED: Add to `test_cli.py` — `test_domain_binance_spot_accepted`, `test_domain_unknown_rejected_with_message`, `test_binance_adapter_selection` (domain→BinanceAdapter with ws_url/rest_url), `test_binance_symbols_lowercased` (BTCUSDT→btcusdt), `test_binance_empty_symbols_exits_1`
- [x] 2.4 GREEN: Add to `src/trady_ai/cli/main.py` `session()` — validate domain `{"FOOTBALL-WINNER","CRYPTO-BINARY","BINANCE-SPOT"}`, unknown→error+exit 1, BINANCE-SPOT→`BinanceAdapter(settings.binance_ws_url, settings.binance_rest_url)` with `[s.lower() for s in settings.get_active_symbols()]`; add Binance `# ── Binance Connection ──` section to `.env.example`

## Phase 3: Guard Script + Integration

- [x] 3.1 RED: Add to `tests/unit/test_ensure_active_market.py` — `test_static_domain_pass` (valid symbols exit 0, `.env` untouched), `test_static_domain_empty` (exit 1), `test_static_domain_lowercase_rejected`, `test_static_domain_invalid_chars_rejected`, `test_valid_domains_includes_binance_spot`
- [x] 3.2 GREEN: Add to `scripts/ensure_active_market.py` — `"BINANCE-SPOT"` in `_VALID_DOMAINS`, `_static_domain_pass(env)` reads `TRADY_AI_ACTIVE_SYMBOLS`, validates uppercase alphanumeric+comma, exit 0 valid / exit 1 empty/invalid; early `if domain == "BINANCE-SPOT": return _static_domain_pass(env)` branch in `main()`
- [x] 3.3 GREEN: Run `pytest` full suite — existing 199+ tests pass, new tests pass; `mypy src/` strict clean; `ruff check .` clean
