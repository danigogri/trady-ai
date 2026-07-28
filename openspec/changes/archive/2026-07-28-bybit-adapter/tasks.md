# Tasks: Bybit Spot Adapter

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~288 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | ask-always |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Adapter + config + guard + integration | PR 1 | `pytest tests/unit/test_bybit_adapter.py -v` | `python -m trady_ai paper-trade session --domain BYBIT-SPOT` (dry-run, valid symbols in .env) | Delete `bybit.py`, revert `settings.py`/`main.py`/`ensure_active_market.py`/`.env.example` — zero core impact |

## Phase 1: BybitAdapter (core)

- [x] 1.1 RED: Create `tests/unit/test_bybit_adapter.py` — `test_market_to_input_valid` (T→timestamp, s→uppercase market_id, p/v→Decimal, source="bybit"), `test_market_to_input_missing_key` (KeyError on absent T/v), `test_market_to_input_invalid_decimal` (ValueError/DecimalException on non-numeric p), `test_market_to_input_idempotent` (same input == same MarketInput), `test_constructor` (stores ws_url/rest_url)
- [x] 1.2 RED: Add to same test file — `test_subscribe_empty_symbols` (ValueError), `test_subscribe_ws_mock_single_trade` (mock connect, assert subscribe `{"op":"subscribe","args":["publicTrade.BTCUSDT"]}`, single-element `data[]` yields one dict), `test_subscribe_ws_mock_multi_batch` (multi-element `data[]` yields one dict per trade), `test_subscribe_multi_symbol` (args contain `publicTrade.BTCUSDT` and `publicTrade.ETHUSDT`), `test_subscribe_non_json_skip` (log warning, continue, not yielded)
- [x] 1.3 GREEN: Create `src/trady_ai/adapters/bybit.py` — `BybitAdapter(ws_url, rest_url)` constructor; `market_to_input(raw)` static: T→`datetime.fromtimestamp(T/1000, UTC)`, s→`.upper()`, p/v→`Decimal`, source=`"bybit"`
- [x] 1.4 GREEN: Implement `subscribe_websocket(symbols)` — `websockets.connect(ws_url)`, send `{"op":"subscribe","args":[f"publicTrade.{s}" for s in symbols]}`, iterate `msg["data"]` yielding each dict individually, log+warn+skip non-JSON, clean exit on close frame
- [x] 1.5 GREEN: Run `pytest tests/unit/test_bybit_adapter.py -v` — all 1.1–1.2 tests pass (20/20)

## Phase 2: Configuration

- [x] 2.1 GREEN: Add to `src/trady_ai/config/settings.py` — `bybit_ws_url: str` (default `wss://stream-testnet.bybit.com/v5/public/spot`), `bybit_rest_url: str` (default `https://api-testnet.bybit.com`); verify immutability
- [x] 2.2 GREEN: Add `# ── Bybit Connection ──` section to `.env.example` — document `TRADY_AI_BYBIT_WS_URL`, `TRADY_AI_BYBIT_REST_URL` with inline comments showing defaults, reference `TRADY_AI_ACTIVE_SYMBOLS`
- [x] 2.3 TEST: Extend `test_config.py` — `test_bybit_settings_defaults`, `test_bybit_settings_explicit_override`, `test_bybit_settings_immutable` (FrozenInstanceError)

## Phase 3: Guard Script + Integration

- [x] 3.1 RED: Add to `tests/unit/test_ensure_active_market.py` — `test_bybit_spot_in_valid_domains` (assert `"BYBIT-SPOT" in _VALID_DOMAINS`), `test_bybit_spot_triggers_static_mode` (no HTTP to Polymarket, exit 0)
- [x] 3.2 GREEN: Add `"BYBIT-SPOT"` to `_VALID_DOMAIN_SET` in `src/trady_ai/cli/main.py`, add `elif domain == "BYBIT-SPOT"` branch — `BybitAdapter(settings.bybit_ws_url, settings.bybit_rest_url)`, symbols UPPERCASE (no `.lower()`), `market_ids = list(symbols)`; add to guard `_VALID_DOMAINS` and `elif domain == "BYBIT-SPOT": return _static_domain_pass(env)`
- [x] 3.3 GREEN: Run full suite — `pytest` (644/645 unit tests pass; 1 pre-existing Binance WS mock failure), `ruff check .` clean
