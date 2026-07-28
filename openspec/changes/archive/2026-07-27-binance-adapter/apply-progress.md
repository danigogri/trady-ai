# Apply Progress: Binance Spot Adapter

**Status**: ✅ Complete — 12/12 tasks done
**Mode**: Strict TDD (pytest)
**Delivery**: Single PR, size:exception accepted by maintainer

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `pytest tests/unit/test_binance_adapter.py -v` → 14 passed |
| Runtime harness command/scenario and exact result | `python -m trady_ai paper-trade session --domain BINANCE-SPOT --non-interactive --duration 1` (dry-run with valid symbols; requires WS connection — integration-level) |
| Rollback boundary | Delete `binance.py`, revert `settings.py`/`main.py`/`ensure_active_market.py`/`.env.example` — zero core impact |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `test_binance_adapter.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 9 cases | ➖ None needed |
| 1.2 | `test_binance_adapter.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 4 cases | ➖ None needed |
| 1.3 | `src/adapters/binance.py` | Unit | N/A (new) | ✅ 1.1 | ✅ Passed | ✅ 9 cases | ➖ None needed |
| 1.4 | `src/adapters/binance.py` | Unit | N/A (new) | ✅ 1.2 | ✅ Passed | ✅ 4 cases | ➖ None needed |
| 1.5 | — | — | ✅ 579/579 | — | ✅ 14/14 | — | ➖ None needed |
| 2.1 | `test_config.py` | Unit | ✅ 7/7 | ✅ Written | ✅ Passed | ✅ 7 cases | ➖ None needed |
| 2.2 | `settings.py` | — | ✅ 14/14 | — | ✅ 14/14 | ➖ Single (structural config) | ➖ None needed |
| 2.3 | `test_cli.py` | CLI | ✅ 14/14 | ✅ Written | ✅ Passed | ✅ 5 cases | ➖ None needed |
| 2.4 | `main.py` + `.env.example` | CLI | ✅ 19/19 | — | ✅ 19/19 | ➖ Single | ➖ None needed |
| 3.1 | `test_ensure_active_market.py` | Unit | ✅ 50/50 | ✅ Written | ✅ Passed | ✅ 7 cases | ➖ None needed |
| 3.2 | `ensure_active_market.py` | — | ✅ 57/57 | — | ✅ 57/57 | ➖ Single | ➖ None needed |
| 3.3 | Full suite | All | ✅ 579/579 | — | ✅ 613/613 | — | ➖ None needed |

### Test Summary
- **Total tests written**: 34 new (14 adapter + 7 config + 5 CLI + 7 guard + 1 integration helper)
- **Total tests passing**: 613 (unit), 1 pre-existing integration failure unchanged
- **Layers used**: Unit (34), CLI (integration via CliRunner)
- **Approval tests**: None — no refactoring tasks
- **Pure functions created**: `BinanceAdapter.market_to_input()` (static pure function), `_static_domain_pass()`, `get_active_symbols()`

## Completed Tasks

### Phase 1: BinanceAdapter (core)
- [x] 1.1 RED: Create `tests/unit/test_binance_adapter.py` — market_to_input tests (valid, missing key, invalid decimal, idempotent, lowercase, large volume)
- [x] 1.2 RED: Add constructor, subscribe_websocket tests (empty→ValueError, single/multi symbol, non-JSON skip)
- [x] 1.3 GREEN: Create `BinanceAdapter` with constructor and `market_to_input` static method
- [x] 1.4 GREEN: Implement `subscribe_websocket` with internal asyncio loop, SUBSCRIBE messaging, non-JSON handling
- [x] 1.5 GREEN: 14/14 tests pass

### Phase 2: Configuration
- [x] 2.1 RED: Add binance settings tests (default URLs, override, get_active_symbols parsing)
- [x] 2.2 GREEN: Add `binance_ws_url`, `binance_rest_url`, `active_symbols` fields + `get_active_symbols()` method
- [x] 2.3 RED: Add CLI domain routing tests (BINANCE-SPOT accepted, unknown rejected, adapter selection)
- [x] 2.4 GREEN: Add domain validation, BINANCE-SPOT→BinanceAdapter routing, `.env.example` section

### Phase 3: Guard Script + Integration
- [x] 3.1 RED: Add guard script tests (valid/invalid/empty symbols, lowercase rejected, whitespace)
- [x] 3.2 GREEN: Add `_static_domain_pass()`, BINANCE-SPOT to `_VALID_DOMAINS`, early branch in `main()`
- [x] 3.3 GREEN: 613 unit tests pass, mypy clean (1 pre-existing error), ruff clean on changed files

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `src/trady_ai/adapters/binance.py` | **Created** | `BinanceAdapter` class: constructor, `subscribe_websocket()`, `market_to_input()` |
| `src/trady_ai/config/settings.py` | **Modified** | Added `binance_ws_url`, `binance_rest_url`, `active_symbols`, `get_active_symbols()` |
| `src/trady_ai/cli/main.py` | **Modified** | Added `_VALID_DOMAIN_SET`, domain validation, BINANCE-SPOT→BinanceAdapter routing |
| `scripts/ensure_active_market.py` | **Modified** | Added `_static_domain_pass()`, `BINANCE-SPOT` in `_VALID_DOMAINS`, early static branch |
| `.env.example` | **Modified** | Added `# ── Binance Connection ──` section, updated Domain section |
| `tests/unit/test_binance_adapter.py` | **Created** | 14 tests: market_to_input (9), constructor (1), subscribe_websocket (4) |
| `tests/unit/test_config.py` | **Modified** | Added 7 binance settings tests |
| `tests/unit/test_cli.py` | **Modified** | Added 5 BINANCE-SPOT domain routing tests |
| `tests/unit/test_ensure_active_market.py` | **Modified** | Added 7 static domain pass tests |

## Deviations from Design
None — implementation matches design.md.

## Issues Found
- Pre-existing integration test failure in `test_paper_trading_session.py` (Polymarket WS connection)
- mypy error in `reflection/persistence.py:135` is pre-existing (not our code)

## Workload / PR Boundary
- **Mode**: single PR
- **Boundary**: Full adapter + config + CLI + guard implementation in one batch
- **Estimated review budget impact**: ~355 lines changed across 9 files
