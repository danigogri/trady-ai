# CLI Domain Support Specification

## Purpose

Extend the CLI to support `--domain BINANCE-SPOT` and `--domain BYBIT-SPOT` for paper trading sessions.
When one of these domains is selected, the session SHALL wire the corresponding adapter (`BinanceAdapter`
or `BybitAdapter`) instead of `PolymarketAdapter`. The CLI SHALL validate the domain against known
values and provide clear error messages for unknown domains.

*Ref: proposal §Affected Areas — cli/main.py*

## Requirements

| Req | Title | Strength | Summary |
|-----|-------|----------|---------|
| REQ-CLI-001 | Domain Flag Acceptance | MUST | `--domain BINANCE-SPOT` and `--domain BYBIT-SPOT` accepted by `paper-trade session` |
| REQ-CLI-002 | Adapter Selection | MUST | `BINANCE-SPOT` maps to `BinanceAdapter`, `BYBIT-SPOT` maps to `BybitAdapter` |
| REQ-CLI-003 | Domain Validation | MUST | Validate domain against known values, error on unknown |
| REQ-CLI-004 | Symbol → Adapter Wiring | MUST | Pass `TRADY_AI_ACTIVE_SYMBOLS` to the selected adapter |

### REQ-CLI-001: Domain Flag Acceptance

The `paper-trade session` command SHALL accept `--domain BINANCE-SPOT` and `--domain BYBIT-SPOT`
as valid options. The domain parameter type remains a free-form string; validation happens inside
the command handler, not at the Click parameter level.

#### Scenario: BINANCE-SPOT accepted

- GIVEN the CLI is invoked
- WHEN running `trady-ai paper-trade session --domain BINANCE-SPOT`
- THEN the command processes without a "domain not recognized" error

#### Scenario: BYBIT-SPOT accepted

- GIVEN the CLI is invoked
- WHEN running `trady-ai paper-trade session --domain BYBIT-SPOT`
- THEN the command processes without a "domain not recognized" error

#### Scenario: Existing domains still work

- GIVEN the CLI is invoked with `--domain FOOTBALL-WINNER`, `--domain CRYPTO-BINARY`, or `--domain BINANCE-SPOT`
- WHEN the command runs
- THEN existing behavior is preserved (no regression)

### REQ-CLI-002: Adapter Selection

When `--domain BINANCE-SPOT` is specified, the session command SHALL instantiate
`BinanceAdapter` with the configured `binance_ws_url` and `binance_rest_url`
from settings, and pass it to `PaperTradingSession`. When `--domain BYBIT-SPOT`
is specified, the session command SHALL instantiate `BybitAdapter` with the
configured `bybit_ws_url` and `bybit_rest_url`. The existing `PolymarketAdapter`
path SHALL remain unchanged for other domains.

#### Scenario: BinanceAdapter instantiated

- GIVEN `settings.binance_ws_url` and `settings.binance_rest_url` are configured
- WHEN domain is `BINANCE-SPOT`
- THEN `BinanceAdapter(ws_url=settings.binance_ws_url, rest_url=settings.binance_rest_url)` is created
- AND passed to `PaperTradingSession(db, adapter=binance_adapter)`

#### Scenario: BybitAdapter instantiated

- GIVEN `settings.bybit_ws_url` and `settings.bybit_rest_url` are configured
- WHEN domain is `BYBIT-SPOT`
- THEN `BybitAdapter(ws_url=settings.bybit_ws_url, rest_url=settings.bybit_rest_url)` is created
- AND passed to `PaperTradingSession(db, adapter=bybit_adapter)`

#### Scenario: Binance symbols passed lowercase

- GIVEN `settings.active_symbols` returns `["BTCUSDT", "ETHUSDT"]`
- WHEN the Binance adapter is wired for a session
- THEN symbols are passed as lowercase `["btcusdt", "ethusdt"]` to `subscribe_websocket()`

#### Scenario: Bybit symbols passed uppercase

- GIVEN `settings.active_symbols` returns `["BTCUSDT", "ETHUSDT"]`
- WHEN the Bybit adapter is wired for a session
- THEN symbols are passed as uppercase `["BTCUSDT", "ETHUSDT"]` to `subscribe_websocket()`

### REQ-CLI-003: Domain Validation

The CLI SHALL validate `--domain` against a known set of valid domains:
`FOOTBALL-WINNER`, `CRYPTO-BINARY`, `BINANCE-SPOT`, `BYBIT-SPOT`. Unknown domains SHALL produce
an error message listing the valid options and exit with code 1.

#### Scenario: Unknown domain rejected

- GIVEN `--domain NONSENSE`
- WHEN the `session` command runs
- THEN an error message is printed: "Unknown domain: NONSENSE. Valid domains: FOOTBALL-WINNER, CRYPTO-BINARY, BINANCE-SPOT, BYBIT-SPOT"
- AND the command exits with code 1

#### Scenario: BINANCE-SPOT validation passes

- GIVEN `--domain BINANCE-SPOT`
- WHEN the `session` command validates the domain
- THEN validation passes, no error

#### Scenario: BYBIT-SPOT validation passes

- GIVEN `--domain BYBIT-SPOT`
- WHEN the `session` command validates the domain
- THEN validation passes, no error

### REQ-CLI-004: Symbol to Adapter Wiring

When domain is `BINANCE-SPOT`, the CLI SHALL read `TRADY_AI_ACTIVE_SYMBOLS`
from settings and convert them to lowercase before passing to the adapter.
The guard script already ensures symbols are valid and uppercase in `.env`;
the CLI lowercase conversion follows Binance's stream name convention
(`<symbol>@trade` where symbol is always lowercase).

When domain is `BYBIT-SPOT`, the CLI SHALL read `TRADY_AI_ACTIVE_SYMBOLS`
from settings and pass them to the adapter as-is (uppercase). Bybit stream
names use the uppercase symbol directly in `publicTrade.<SYMBOL>` — no case
conversion needed.

#### Scenario: Binance symbol case conversion

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT`
- WHEN the CLI wires symbols to `BinanceAdapter`
- THEN `subscribe_websocket(["btcusdt", "ethusdt"])` is called (lowercase)

#### Scenario: Bybit symbols passed as-is

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT`
- WHEN the CLI wires symbols to `BybitAdapter`
- THEN `subscribe_websocket(["BTCUSDT", "ETHUSDT"])` is called (uppercase, no conversion)

#### Scenario: No symbols configured

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS` is empty
- WHEN domain is `BINANCE-SPOT` or `BYBIT-SPOT`
- THEN the CLI prints an error: "No symbols configured. Set TRADY_AI_ACTIVE_SYMBOLS in .env"
- AND exits with code 1

---

**Boundary**: The CLI is responsible for adapter selection and wiring. It does
not modify the `PaperTradingSession` contract — the session is adapter-agnostic
and receives whichever adapter the CLI provides. Domain validation is a
presentation-layer concern; core layers never reference domain identifiers.
