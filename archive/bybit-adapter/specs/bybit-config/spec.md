# Bybit Configuration Specification

## Purpose

Configuration contract for Bybit testnet connectivity. Defines environment
variables and `Settings` fields required by `BybitAdapter`. Follows the existing
pydantic-settings pattern with `TRADY_AI_` prefix and frozen immutability.
Reuses `TRADY_AI_ACTIVE_SYMBOLS` (same field as Binance).

*Ref: proposal §Capabilities — binance-config (modified), platform co-location*

## Requirements

| Req | Title | Strength | Summary |
|-----|-------|----------|---------|
| REQ-BYC-001 | WebSocket URL | MUST | `BYBIT_WS_URL` env var, default `wss://stream-testnet.bybit.com/v5/public/spot` |
| REQ-BYC-002 | REST URL | MUST | `BYBIT_REST_URL` env var, default `https://api-testnet.bybit.com` |
| REQ-BYC-003 | Active Symbols Reuse | MUST | Reuse `TRADY_AI_ACTIVE_SYMBOLS` as source of trading pairs |
| REQ-BYC-004 | Domain Value | MUST | `TRADY_AI_DOMAIN=BYBIT-SPOT` as valid domain |
| REQ-BYC-005 | Settings Fields | MUST | `bybit_ws_url`, `bybit_rest_url` on Settings class |
| REQ-BYC-006 | .env.example | MUST | Document Bybit vars in `.env.example` |

### REQ-BYC-001: Bybit WebSocket URL

`TRADY_AI_BYBIT_WS_URL` SHALL specify the Bybit WebSocket endpoint. When unset,
it SHALL default to `wss://stream-testnet.bybit.com/v5/public/spot`.

#### Scenario: Default value

- GIVEN `.env` has no `TRADY_AI_BYBIT_WS_URL` entry
- WHEN `get_settings()` is called
- THEN `settings.bybit_ws_url == "wss://stream-testnet.bybit.com/v5/public/spot"`

#### Scenario: Explicit override

- GIVEN `.env` contains `TRADY_AI_BYBIT_WS_URL=wss://stream.bybit.com/v5/public/spot`
- WHEN `get_settings()` is called
- THEN `settings.bybit_ws_url == "wss://stream.bybit.com/v5/public/spot"`

### REQ-BYC-002: Bybit REST URL

`TRADY_AI_BYBIT_REST_URL` SHALL specify the Bybit REST API base URL. When
unset, it SHALL default to `https://api-testnet.bybit.com`.

#### Scenario: Default value

- GIVEN `.env` has no `TRADY_AI_BYBIT_REST_URL` entry
- WHEN `get_settings()` is called
- THEN `settings.bybit_rest_url == "https://api-testnet.bybit.com"`

### REQ-BYC-003: Active Symbols Reuse

`TRADY_AI_ACTIVE_SYMBOLS` SHALL serve as the symbol source for Bybit, identical
to its use for Binance. The existing `get_active_symbols()` helper returns the
parsed list. No separate Bybit-specific symbol env var is needed.

#### Scenario: Symbols shared

- GIVEN `.env` contains `TRADY_AI_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT`
- WHEN domain is `BYBIT-SPOT` and `settings.get_active_symbols()` is called
- THEN returns `["BTCUSDT", "ETHUSDT"]`

### REQ-BYC-004: Domain Value BYBIT-SPOT

`BYBIT-SPOT` SHALL be a valid value for `TRADY_AI_DOMAIN`. The guard script and
CLI SHALL accept it alongside `FOOTBALL-WINNER`, `CRYPTO-BINARY`, and
`BINANCE-SPOT`.

#### Scenario: Valid domain

- GIVEN `.env` contains `TRADY_AI_DOMAIN=BYBIT-SPOT`
- WHEN the guard script or CLI reads the domain
- THEN recognized as valid and proceeds without error

### REQ-BYC-005: Settings Fields

The `Settings` class SHALL include two new fields:

| Field | Type | Default |
|-------|------|---------|
| `bybit_ws_url` | `str` | `"wss://stream-testnet.bybit.com/v5/public/spot"` |
| `bybit_rest_url` | `str` | `"https://api-testnet.bybit.com"` |

All SHALL be immutable (`frozen=True`), loaded via `TRADY_AI_` prefix.

#### Scenario: Fields accessible

- GIVEN `get_settings()` returns an instance
- WHEN accessing `settings.bybit_ws_url`, `settings.bybit_rest_url`
- THEN both attributes exist and return their configured values

#### Scenario: Immutable

- GIVEN a `Settings` instance
- WHEN attempting `settings.bybit_ws_url = "changed"`
- THEN `ValidationError` or `FrozenInstanceError` is raised

### REQ-BYC-006: .env.example Documentation

The `.env.example` file SHALL include a `# ── Bybit Connection ──` section
documenting `TRADY_AI_BYBIT_WS_URL`, `TRADY_AI_BYBIT_REST_URL`, and referencing
`TRADY_AI_ACTIVE_SYMBOLS` with inline comments.

#### Scenario: Env example complete

- GIVEN `.env.example` is read
- WHEN searching for "Bybit"
- THEN a section exists with Bybit vars commented and default values shown

---

**Boundary**: Settings are immutable post-construction. `TRADY_AI_ACTIVE_SYMBOLS`
is shared across Binance and Bybit — only one domain is active per session.
Discovery of active symbols is static (configured, not API-queried) — this is
the defining characteristic of `BYBIT-SPOT` domain mode.
