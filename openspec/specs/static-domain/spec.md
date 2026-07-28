# Static Domain — Guard Script Specification

## Purpose

When `TRADY_AI_DOMAIN=BINANCE-SPOT`, the `ensure_active_market.py` guard script
operates in static mode: it does NOT perform market discovery (no Polymarket API
calls). Instead, it validates `TRADY_AI_ACTIVE_SYMBOLS` from `.env`, confirms
the format is valid, and exits 0. Binance trading pairs do not expire — no
rotation is needed.

*Ref: proposal §Affected Areas — scripts/guard.py*

## Requirements

| Req | Title | Strength | Summary |
|-----|-------|----------|---------|
| REQ-SD-001 | No Market Discovery | MUST | Skip all Polymarket API calls when domain is BINANCE-SPOT |
| REQ-SD-002 | Symbol Validation | MUST | Validate `TRADY_AI_ACTIVE_SYMBOLS` format before proceeding |
| REQ-SD-003 | Exit 0 — No Rotation | MUST | Return 0 without writing `.env` (symbols don't expire) |
| REQ-SD-004 | Error on Missing Symbols | MUST | Exit 1 if `TRADY_AI_ACTIVE_SYMBOLS` is empty or unset |
| REQ-SD-005 | Valid Domain Set | MUST | Include `BINANCE-SPOT` in `_VALID_DOMAINS` |

### REQ-SD-001: No Market Discovery

When `TRADY_AI_DOMAIN=BINANCE-SPOT`, the guard script SHALL NOT make any HTTP
requests to Polymarket APIs (`clob.polymarket.com`, `gamma-api.polymarket.com`,
`polymarket.com/sports`). The static branch is a pure I/O path: read `.env`,
validate, exit.

#### Scenario: No API calls

- GIVEN `TRADY_AI_DOMAIN=BINANCE-SPOT`, `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT`
- WHEN `ensure_active_market.py` runs
- THEN no HTTP request is made to any Polymarket endpoint
- AND the script exits 0

#### Scenario: Guard recognizes static domain

- GIVEN `_VALID_DOMAINS` includes `"BINANCE-SPOT"`
- WHEN `_load_discovery_config({"TRADY_AI_DOMAIN": "BINANCE-SPOT"})` is called
- THEN the domain is accepted without error
- AND the returned config indicates a static domain (no tag_slug, leagues, or patterns required)

### REQ-SD-002: Symbol Validation

The guard SHALL validate that `TRADY_AI_ACTIVE_SYMBOLS` contains only valid
trading pair identifiers: uppercase alphanumeric characters, separated by
commas. No other characters (spaces are stripped, not rejected).

#### Scenario: Valid symbols

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT`
- WHEN the guard validates symbols
- THEN validation passes, and the symbols are accepted

#### Scenario: Single symbol

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT`
- WHEN the guard validates symbols
- THEN validation passes

#### Scenario: Lowercase symbols (rejected)

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS=btcusdt,ethusdt`
- WHEN the guard validates symbols
- THEN validation fails with an error message indicating symbols must be uppercase

#### Scenario: Whitespace handling

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS= BTCUSDT , ETHUSDT `
- WHEN symbols are parsed
- THEN the result is `["BTCUSDT", "ETHUSDT"]` (whitespace stripped, not rejected)

#### Scenario: Invalid characters

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS=BTC-USDT,ETH*USDT`
- WHEN the guard validates symbols
- THEN validation fails with an error indicating invalid characters

### REQ-SD-003: Exit 0 — No Rotation

Since Binance trading pairs do not expire, the guard SHALL always exit 0 when
symbols are valid and present. It SHALL NOT write to `.env` (no rotation needed).

#### Scenario: Exit with valid symbols

- GIVEN valid symbols configured
- WHEN guard runs with `BINANCE-SPOT` domain
- THEN exits 0, `.env` is NOT modified

### REQ-SD-004: Error on Missing Symbols

If `TRADY_AI_ACTIVE_SYMBOLS` is empty, unset, or contains only whitespace, the
guard SHALL log an error and exit 1. The session cannot proceed without symbols.

#### Scenario: Empty symbols

- GIVEN `TRADY_AI_ACTIVE_SYMBOLS=` (empty)
- WHEN guard runs with `BINANCE-SPOT` domain
- THEN logs error: "active_symbols_required for BINANCE-SPOT"
- AND exits 1

#### Scenario: Symbols not set

- GIVEN `.env` has no `TRADY_AI_ACTIVE_SYMBOLS` entry
- WHEN guard runs with `BINANCE-SPOT` domain
- THEN exits 1

### REQ-SD-005: Valid Domain Set Update

The `_VALID_DOMAINS` set in `ensure_active_market.py` SHALL include
`"BINANCE-SPOT"` alongside existing values. The domain routing logic SHALL have
an `elif domain == "BINANCE-SPOT"` branch that invokes the static path before
falling through to the league-based default.

#### Scenario: Domain routing

- GIVEN `_VALID_DOMAINS = {"FOOTBALL-WINNER", "CRYPTO-BINARY", "BINANCE-SPOT"}`
- WHEN domain is `"BINANCE-SPOT"`
- THEN static validation branch executes (no discovery attempt)

#### Scenario: Error message includes BINANCE-SPOT

- GIVEN an invalid domain value
- WHEN guard exits with error
- THEN the error message lists `FOOTBALL-WINNER, CRYPTO-BINARY, BINANCE-SPOT` as valid options

---

**Boundary**: Static domain mode is a guard-level concern only. Downstream code
(`EventCapture`, `PaperTradingSession`) is domain-agnostic — the adapter is
selected by the caller, not by the guard. The guard's only role in static mode
is pre-flight validation and pass-through.
