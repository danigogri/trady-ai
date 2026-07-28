# Binance Configuration Specification

## Purpose

Configuration contract for Binance testnet connectivity. Defines the environment
variables and `Settings` fields required by `BinanceAdapter`. Follows the
existing pydantic-settings pattern with `TRADY_AI_` prefix and frozen immutability.

*Ref: proposal §Affected Areas — config/settings.py*

## Requirements

| Req | Title | Strength | Summary |
|-----|-------|----------|---------|
| REQ-BC-001 | WebSocket URL | MUST | `BINANCE_WS_URL` env var with default `wss://testnet.binance.vision/ws` |
| REQ-BC-002 | REST URL | MUST | `BINANCE_REST_URL` env var with default `https://testnet.binance.vision` |
| REQ-BC-003 | Active Symbols | MUST | `TRADY_AI_ACTIVE_SYMBOLS` env var, comma-separated trading pairs |
| REQ-BC-004 | Domain Value | MUST | `TRADY_AI_DOMAIN=BINANCE-SPOT` as a new valid domain |
| REQ-BC-005 | Settings Fields | MUST | `binance_ws_url`, `binance_rest_url`, `active_symbols` on Settings class |
| REQ-BC-006 | .env.example | MUST | Document new vars with comments in `.env.example` |

### REQ-BC-001: Binance WebSocket URL

The `TRADY_AI_BINANCE_WS_URL` environment variable SHALL specify the Binance
WebSocket endpoint. When unset, it SHALL default to
`wss://testnet.binance.vision/ws`.

#### Scenario: Default value

- GIVEN `.env` has no `TRADY_AI_BINANCE_WS_URL` entry
- WHEN `get_settings()` is called
- THEN `settings.binance_ws_url == "wss://testnet.binance.vision/ws"`

#### Scenario: Explicit override

- GIVEN `.env` contains `TRADY_AI_BINANCE_WS_URL=wss://stream.binance.com:9443/ws`
- WHEN `get_settings()` is called
- THEN `settings.binance_ws_url == "wss://stream.binance.com:9443/ws"`

### REQ-BC-002: Binance REST URL

The `TRADY_AI_BINANCE_REST_URL` environment variable SHALL specify the Binance
REST API base URL. When unset, it SHALL default to
`https://testnet.binance.vision`.

#### Scenario: Default value

- GIVEN `.env` has no `TRADY_AI_BINANCE_REST_URL` entry
- WHEN `get_settings()` is called
- THEN `settings.binance_rest_url == "https://testnet.binance.vision"`

### REQ-BC-003: Active Symbols

The `TRADY_AI_ACTIVE_SYMBOLS` environment variable SHALL hold a comma-separated
list of trading pairs (e.g., `"BTCUSDT,ETHUSDT"`). The `Settings` class SHALL
expose this as a string field and provide a `get_active_symbols()` helper method
that returns `list[str]`.

#### Scenario: Multiple symbols

- GIVEN `.env` contains `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT`
- WHEN `settings.get_active_symbols()` is called
- THEN returns `["BTCUSDT", "ETHUSDT", "BNBUSDT"]`

#### Scenario: Empty / unset

- GIVEN `.env` has no `TRADY_AI_ACTIVE_SYMBOLS` entry
- WHEN `settings.get_active_symbols()` is called
- THEN returns `[]`

#### Scenario: Whitespace tolerance

- GIVEN `.env` contains `TRADY_AI_ACTIVE_SYMBOLS= BTCUSDT , ETHUSDT `
- WHEN `settings.get_active_symbols()` is called
- THEN returns `["BTCUSDT", "ETHUSDT"]` (stripped)

### REQ-BC-004: Domain Value BINANCE-SPOT

`BINANCE-SPOT` SHALL be a valid value for `TRADY_AI_DOMAIN`. The guard script
and CLI SHALL accept it alongside existing values `FOOTBALL-WINNER` and
`CRYPTO-BINARY`.

#### Scenario: Valid domain

- GIVEN `.env` contains `TRADY_AI_DOMAIN=BINANCE-SPOT`
- WHEN the guard script or CLI reads the domain
- THEN it is recognized as valid and proceeds without error

### REQ-BC-005: Settings Fields

The `Settings` class SHALL include three new fields:

| Field | Type | Default |
|-------|------|---------|
| `binance_ws_url` | `str` | `"wss://testnet.binance.vision/ws"` |
| `binance_rest_url` | `str` | `"https://testnet.binance.vision"` |
| `active_symbols` | `str` | `""` |

All SHALL be immutable (`frozen=True`), loaded via `TRADY_AI_` prefix.

#### Scenario: Fields accessible

- GIVEN `get_settings()` returns an instance
- WHEN accessing `settings.binance_ws_url`, `settings.binance_rest_url`, `settings.active_symbols`
- THEN all three attributes exist and return their configured values

#### Scenario: Immutable

- GIVEN a `Settings` instance
- WHEN attempting `settings.binance_ws_url = "changed"`
- THEN a `ValidationError` or `FrozenInstanceError` is raised

### REQ-BC-006: .env.example Documentation

The `.env.example` file SHALL include a `# ── Binance Connection ──` section
documenting `TRADY_AI_BINANCE_WS_URL`, `TRADY_AI_BINANCE_REST_URL`, and
`TRADY_AI_ACTIVE_SYMBOLS` with inline comments.

#### Scenario: Env example complete

- GIVEN `.env.example` is read
- WHEN searching for "Binance"
- THEN a section exists with all three vars commented and default values shown

---

**Boundary**: Settings are immutable post-construction. No runtime config
changes. Discovery of active symbols is static (configured, not API-queried) —
this is the defining characteristic of `BINANCE-SPOT` domain mode.
