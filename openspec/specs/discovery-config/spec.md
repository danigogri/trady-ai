# Discovery Config Specification

## Purpose

Domain-agnostic configuration for `ensure_active_market.py`. Every guard run loads and validates its config deterministically. Same `.env` → same behavior, always.

*Ref: proposal §Approach items 1, 4; AD-5 (externalized rules)*

## Requirements

### REQ-DC-001: Domain Selection

The guard SHALL read `TRADY_AI_DOMAIN` from `.env`. Accepted values: `FOOTBALL-WINNER`, `CRYPTO-BINARY`. When unset, the guard SHALL default to `FOOTBALL-WINNER`.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Explicit domain | `TRADY_AI_DOMAIN=CRYPTO-BINARY` | guard runs | uses `CRYPTO-BINARY` strategy |
| Domain unset (fallback) | `TRADY_AI_DOMAIN` absent | guard runs | defaults to `FOOTBALL-WINNER` |
| Invalid value | `TRADY_AI_DOMAIN=NONSENSE` | guard runs | logs error with valid domain list, exits 1 |

### REQ-DC-002: Tag Slug Validation for Tag-Based Domains

When `TRADY_AI_DOMAIN` maps to a tag-based strategy (e.g., `CRYPTO-BINARY`), the guard SHALL read `TRADY_AI_DISCOVERY_TAG_SLUG`. The value MUST be a non-empty slug string.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Required and present | `DOMAIN=CRYPTO-BINARY`, `DISCOVERY_TAG_SLUG=crypto` | guard runs | proceeds with tag-based discovery |
| Required but missing | `DOMAIN=CRYPTO-BINARY`, `DISCOVERY_TAG_SLUG` absent | guard runs | logs error, exits 1 |
| Required but empty | `DOMAIN=CRYPTO-BINARY`, `DISCOVERY_TAG_SLUG=""` | guard runs | logs error, exits 1 |
| Not required | `DOMAIN=FOOTBALL-WINNER`, `DISCOVERY_TAG_SLUG` absent | guard runs | proceeds normally (no validation) |

### REQ-DC-003: Legacy Variable Backward Compatibility

Legacy vars `TRADY_AI_FOOTBALL_LEAGUES`, `TRADY_AI_WINNER_PATTERN`, and `TRADY_AI_REJECT_PATTERNS` SHALL remain functional. The guard SHALL read them when operating as `FOOTBALL-WINNER` (explicit or defaulted). A deprecation warning SHOULD be logged when legacy vars are used without `TRADY_AI_DOMAIN` explicitly set.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Legacy leagues used | `TRADY_AI_FOOTBALL_LEAGUES=mex,mls`, no `TRADY_AI_DOMAIN` | guard runs | uses `[mex, mls]` league list |
| Legacy absent | no `TRADY_AI_FOOTBALL_LEAGUES`, no `TRADY_AI_DOMAIN` | guard runs | uses frozen defaults |
| Deprecation log | legacy vars present, `TRADY_AI_DOMAIN` unset | guard runs | logs deprecation warning |

---

**Boundary**: Fully deterministic. Config loading is pure I/O — same `.env` bytes produce identical parsed config. No intelligence/live config involved.
