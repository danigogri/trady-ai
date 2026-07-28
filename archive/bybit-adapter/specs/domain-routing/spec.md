# Delta for CLI Domain + Static Domain Routing

*Ref: proposal §Capabilities — cli-domain, static-domain (modified)*

## cli-domain Delta

### MODIFIED Requirements

#### REQ-CLI-001: Domain Flag Acceptance

The `paper-trade session` command SHALL accept `--domain BYBIT-SPOT` as a
valid option. The domain parameter type remains a free-form string; validation
happens inside the command handler, not at the Click parameter level.
(Previously: accepted `FOOTBALL-WINNER`, `CRYPTO-BINARY`, `BINANCE-SPOT` only)

##### Scenario: BYBIT-SPOT accepted

- GIVEN the CLI is invoked
- WHEN running `trady-ai paper-trade session --domain BYBIT-SPOT`
- THEN the command processes without a "domain not recognized" error

##### Scenario: Existing domains still work

- GIVEN the CLI is invoked with `--domain FOOTBALL-WINNER`, `--domain CRYPTO-BINARY`, or `--domain BINANCE-SPOT`
- WHEN the command runs
- THEN existing behavior is preserved (no regression)

#### REQ-CLI-002: Adapter Selection

When `--domain BYBIT-SPOT` is specified, the session command SHALL instantiate
`BybitAdapter` with the configured `bybit_ws_url` and `bybit_rest_url` from
settings, and pass it to `PaperTradingSession`. The `BinanceAdapter` path
(`BINANCE-SPOT`) and `PolymarketAdapter` path (other domains) SHALL remain
unchanged.
(Previously: only `BinanceAdapter` for `BINANCE-SPOT`, `PolymarketAdapter` for others)

##### Scenario: BybitAdapter instantiated

- GIVEN `settings.bybit_ws_url` and `settings.bybit_rest_url` are configured
- WHEN domain is `BYBIT-SPOT`
- THEN `BybitAdapter(ws_url=settings.bybit_ws_url, rest_url=settings.bybit_rest_url)` is created
- AND passed to `PaperTradingSession(db, adapter=bybit_adapter)`

##### Scenario: Symbols passed correctly

- GIVEN `settings.active_symbols` returns `["BTCUSDT", "ETHUSDT"]`
- WHEN the Bybit adapter is wired for a session
- THEN symbols are passed as uppercase `["BTCUSDT", "ETHUSDT"]` to `subscribe_websocket()`

#### REQ-CLI-003: Domain Validation

The CLI SHALL validate `--domain` against the known set:
`FOOTBALL-WINNER`, `CRYPTO-BINARY`, `BINANCE-SPOT`, `BYBIT-SPOT`.
Unknown domains SHALL produce an error listing valid options and exit 1.
(Previously: valid domains did not include `BYBIT-SPOT`)

##### Scenario: Unknown domain rejected

- GIVEN `--domain NONSENSE`
- WHEN the `session` command runs
- THEN error: "Unknown domain: NONSENSE. Valid domains: FOOTBALL-WINNER, CRYPTO-BINARY, BINANCE-SPOT, BYBIT-SPOT"
- AND exits with code 1

##### Scenario: BYBIT-SPOT validation passes

- GIVEN `--domain BYBIT-SPOT`
- WHEN the `session` command validates the domain
- THEN validation passes, no error

#### REQ-CLI-004: Symbol to Adapter Wiring

When domain is `BYBIT-SPOT`, the CLI SHALL read `TRADY_AI_ACTIVE_SYMBOLS`
from settings and pass them to the adapter. Bybit stream names use the
uppercase symbol directly in `publicTrade.<SYMBOL>` — no case conversion needed
(unlike Binance which requires lowercase).
(Previously: only BINANCE-SPOT path existed, with lowercase conversion)

##### Scenario: Symbols passed as-is

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT`
- WHEN the CLI wires symbols to `BybitAdapter`
- THEN `subscribe_websocket(["BTCUSDT", "ETHUSDT"])` is called (uppercase, no conversion)

##### Scenario: No symbols configured

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS` is empty
- WHEN domain is `BYBIT-SPOT`
- THEN CLI prints error: "No symbols configured. Set TRADY_AI_ACTIVE_SYMBOLS in .env"
- AND exits with code 1

## static-domain Delta

### MODIFIED Requirements

#### REQ-SD-001: No Market Discovery

When `TRADY_AI_DOMAIN` is `BINANCE-SPOT` or `BYBIT-SPOT`, the guard script
SHALL NOT make any HTTP requests to Polymarket APIs. The static branch is a
pure I/O path: read `.env`, validate symbols, exit.
(Previously: static mode only applied to `BINANCE-SPOT`)

##### Scenario: BYBIT-SPOT triggers static mode

- GIVEN `TRADY_AI_DOMAIN=BYBIT-SPOT`, `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT`
- WHEN `ensure_active_market.py` runs
- THEN no HTTP request is made to any Polymarket endpoint
- AND the script exits 0

##### Scenario: BINANCE-SPOT static mode preserved

- GIVEN `TRADY_AI_DOMAIN=BINANCE-SPOT`, `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT`
- WHEN `ensure_active_market.py` runs
- THEN no HTTP request is made to any Polymarket endpoint
- AND the script exits 0

#### REQ-SD-005: Valid Domain Set Update

The `_VALID_DOMAINS` set in `ensure_active_market.py` SHALL include
`"BYBIT-SPOT"` alongside `"FOOTBALL-WINNER"`, `"CRYPTO-BINARY"`, and
`"BINANCE-SPOT"`. The domain routing logic SHALL have an
`elif domain == "BYBIT-SPOT"` branch that invokes the static path.
(Previously: `_VALID_DOMAINS` did not include `BYBIT-SPOT`)

##### Scenario: Domain routing includes BYBIT-SPOT

- GIVEN `_VALID_DOMAINS = {"FOOTBALL-WINNER", "CRYPTO-BINARY", "BINANCE-SPOT", "BYBIT-SPOT"}`
- WHEN domain is `"BYBIT-SPOT"`
- THEN static validation branch executes (no discovery attempt)

##### Scenario: Error message includes BYBIT-SPOT

- GIVEN an invalid domain value
- WHEN guard exits with error
- THEN error message lists `FOOTBALL-WINNER, CRYPTO-BINARY, BINANCE-SPOT, BYBIT-SPOT` as valid options

---

**Boundary**: Static domain mode is a guard-level concern. Downstream code
(`EventCapture`, `PaperTradingSession`) is domain-agnostic — the adapter is
selected by the caller, not by the guard. Both `BINANCE-SPOT` and `BYBIT-SPOT`
use the same static path; the difference is only in which adapter the CLI wires.
