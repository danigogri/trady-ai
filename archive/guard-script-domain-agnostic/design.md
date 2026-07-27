# Design: Guard Script Domain-Agnostic Discovery

## Technical Approach

Replace hardcoded football discovery in `main()` with a domain-switch: tag-based domains call gamma-api's `/events?tag_slug=`; league-based domains keep the existing HTML-scraping path. Both strategies share the same eligibility filter (`_is_eligible_market`, renamed from `_is_winner_market`) and output contract (write one `condition_id` to `.env`).

## Script Flow

```
main()
  ├─ _load_env() + _load_discovery_config(env)   ← NEW: reads TRADY_AI_DOMAIN, DISCOVERY_TAG_SLUG
  ├─ Phase 1: Check current markets (unchanged)
  ├─ Phase 2: Rotation if all expired (routed)
  │    ├─ tag-based → _discover_tag_based() → GET /events?tag_slug=...
  │    └─ league-based → _find_eligible_market() per league (unchanged path)
  └─ _write_env() with TRADY_AI_ACTIVE_MARKETS (unchanged)
```

## Config Changes

### `_load_discovery_config(env) → dict` — refactored

**Reads new vars:** `TRADY_AI_DOMAIN` (default: `FOOTBALL-WINNER`), `TRADY_AI_DISCOVERY_TAG_SLUG` (required when domain is tag-based).

**Validation (DC-001, DC-002):** Domain must be in `{FOOTBALL-WINNER, CRYPTO-BINARY}` — invalid → log + exit 1. Tag-based domain requires non-empty `TRADY_AI_DISCOVERY_TAG_SLUG` — missing → log + exit 1. League-based ignores `DISCOVERY_TAG_SLUG`.

**Legacy compat (DC-003):** `TRADY_AI_FOOTBALL_LEAGUES`, `TRADY_AI_WINNER_PATTERN`, `TRADY_AI_REJECT_PATTERNS` read unchanged. New `TRADY_AI_QUESTION_PATTERN` takes precedence over `TRADY_AI_WINNER_PATTERN`. Deprecation warning logged when legacy patterns used without explicit `TRADY_AI_DOMAIN`.

**Return type:** adds `domain: str`, `tag_slug: str | None`. Renames: `_DEFAULT_WINNER_PATTERN` → `_DEFAULT_QUESTION_PATTERN` (line 70), `_is_winner_market()` → `_is_eligible_market()` (line 299), local `winner_pattern` → `question_pattern`.

## Tag-Based Discovery

### `_discover_tag_based(tag_slug, question_pattern, reject_patterns) → str | None`

```python
def _discover_tag_based(
    tag_slug: str,
    question_pattern: re.Pattern[str],
    reject_patterns: list[re.Pattern[str]],
) -> str | None:
```

**API call (TD-001):**
`GET https://gamma-api.polymarket.com/events?tag_slug={tag_slug}&active=true&closed=false&limit=50`
Headers: `User-Agent: trady-ai-discovery/1.0`, `Accept: application/json`. Timeout: 15s.

**Response parsing:** Response is `list[dict]` of events. Each event has `markets: list[dict]`. Walk all markets across all events, apply `_is_eligible_market()`, return first `conditionId` or `condition_id` that also passes `_query_market_active()` CLOB double-check (TD-003).

**Error handling (TD-004):** Non-200 → log `http_get_failed` + exit 1. Empty response/no markets → log `no_markets_found` + exit 1. JSON decode failure → logged by `_http_get_json` (reused). Connection error → surfaced as `URLError`.

## Discovery Routing

**Domain→strategy mapping (DR-001):**
| Domain | Strategy | Function |
|--------|----------|----------|
| `FOOTBALL-WINNER` (default) | league-based | `_find_eligible_market()` per league |
| `CRYPTO-BINARY` | tag-based | `_discover_tag_based()` |

Routing is an `if/elif` in `main()` after Phase 1. Unknown domains are already rejected by `_load_discovery_config()` validation — no fallthrough.

**Extensibility:** Add domain → add to valid set + routing `elif` + discovery function. No config plumbing change.

**Output contract (DR-002):** Both strategies return `condition_id | None`. `main()` writes to `.env` and returns 0/1 identically.

## File Changes Manifest

| File | Change | Lines |
|------|--------|-------|
| `scripts/ensure_active_market.py:44` | Modify | Docstring updated for domain-agnostic discovery |
| `scripts/ensure_active_market.py:70` | Modify | `_DEFAULT_WINNER_PATTERN` → `_DEFAULT_QUESTION_PATTERN` |
| `scripts/ensure_active_market.py:178-227` | Modify | `_load_discovery_config()` extended: domain/tag_slug read, validated, deprecation log |
| `scripts/ensure_active_market.py:228+` | Add | `_discover_tag_based()` (~50 lines) |
| `scripts/ensure_active_market.py:299,321-351` | Modify | Rename `_is_winner_market`→`_is_eligible_market`; `_find_eligible_market` uses `question_pattern` |
| `scripts/ensure_active_market.py:357-436` | Modify | `main()`: destructure new config keys, domain routing `if/elif` in both rotation branches |
| `.env.example:49+` | Add | New `## Domain Configuration` section: `TRADY_AI_DOMAIN`, `TRADY_AI_DISCOVERY_TAG_SLUG`, `TRADY_AI_QUESTION_PATTERN` |
| `tests/unit/test_ensure_active_market.py` | Modify | Rename references (`winner_pattern`→`question_pattern`, `_is_winner_market`→`_is_eligible_market`) |
| `tests/unit/test_ensure_active_market.py` | Add | ~10 tests: domain config (DC-001–003), tag discovery mock (TD-001–004), routing dispatch (DR-001) |

**Deleted:** Nothing. All existing football logic preserved.

## Backward Compatibility

- **Legacy unset domain:** `TRADY_AI_DOMAIN` absent + `TRADY_AI_FOOTBALL_LEAGUES=mex,mls` → defaults to `FOOTBALL-WINNER`. Identical HTTP calls, filter logic, `.env` output as pre-refactor (DR-003).
- **Tag-based domain:** `TRADY_AI_DOMAIN=CRYPTO-BINARY`, `TRADY_AI_DISCOVERY_TAG_SLUG=crypto` → validated, routed to `_discover_tag_based()`, single gamma-api call.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit — config | DC-001 (domain valid/default/invalid), DC-002 (tag_slug required/empty), DC-003 (legacy fallback + deprecation) | Extend `TestLoadDiscoveryConfig` |
| Unit — tag discovery | TD-001 (API→condition_id), TD-002 (filter), TD-003 (CLOB check), TD-004 (error: non-200, empty, JSON, connection) | New `TestDiscoverTagBased`, mock `_http_get_json` + `_query_market_active` |
| Unit — routing | DR-001 (domain dispatch), DR-002 (output contract), DR-003 (football identical) | Extend `TestMainFlow`, mock discovery functions |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR, executable-classification, or process-integration boundary. Pure internal control-flow refactor.

## Migration / Rollout

No migration. `TRADY_AI_DOMAIN` defaults to `FOOTBALL-WINNER` — existing `.env` files work unchanged. Rollback: delete `TRADY_AI_DOMAIN` or set to `FOOTBALL-WINNER`.

## Open Questions

None.
