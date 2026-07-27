# Proposal: Guard Script Domain-Agnostic Discovery

**Phase**: 5 (Paper Trading) | **RFC**: RFC-006 §Domain Isolation, RFC-009 §Operational Continuity

## Intent

`scripts/ensure_active_market.py` is hardcoded to football-winner discovery: scrapes `polymarket.com/sports/{league}/games` HTML, filters by "Will X win on YYYY-MM-DD?" regex. Crypto (and future tag-based domains like politics, science) needs none of this — a single API call suffices. Refactor the guard to support two discovery strategies via a domain config switch, keeping football working with zero operator impact.

## Scope

**In scope:**
- `TRADY_AI_DOMAIN` env var (`FOOTBALL-WINNER` | `CRYPTO-BINARY`)
- `TRADY_AI_DISCOVERY_TAG_SLUG` env var (e.g., `crypto`, `politics`)
- `_discover_tag_based()`: single `GET /events?tag_slug=X&active=true&closed=false&limit=50`
- Route discovery strategy by `TRADY_AI_DOMAIN` in `main()`
- `_load_discovery_config()` reads new vars; legacy football vars still supported
- Update `.env.example`
- 10 new pytest tests for tag-based discovery path

**Out of scope:**
- Multi-market booking (still 1 market at a time)
- Auto-rotation for crypto (markets last months; not needed)
- New domains beyond crypto and football

## Capabilities

### New Capabilities
None — this is a structural refactor within an existing script.

### Modified Capabilities
- `paper-trading`: REQ-PT-009 (Discovery Clock) — guard logic extended to support tag-based discovery. The deterministic contract (first-valid, no ranking, no AI, frozen rules) remains unchanged. Only the *discovery transport* differs per domain.

## Approach

1. Add `TRADY_AI_DOMAIN` and `TRADY_AI_DISCOVERY_TAG_SLUG` to config loading
2. Extract existing HTML scraping into `_discover_league_based(leagues, ...)`
3. Add `_discover_tag_based(tag_slug, ...)`: one gamma-api call, apply same question/reject filters
4. In `main()`, branch on domain type: tag-based → `_discover_tag_based`, else → `_discover_league_based` (backward compat)
5. Legacy vars (`TRADY_AI_FOOTBALL_LEAGUES`, `TRADY_AI_WINNER_PATTERN`) remain read; log deprecation warning when used without `TRADY_AI_DOMAIN` set

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `scripts/ensure_active_market.py` | Modified | Domain routing + tag-based function |
| `.env.example` | Modified | New vars documented |
| `tests/test_ensure_active_market.py` | Modified | 10 new tests for tag path |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Gamma API adds `tag_slug` rate-limiting | Low | Single call per run; 15-min cron rhythm won't trigger limits |
| Legacy football config breaks during refactor | Low | Extract existing logic into named function; guard with existing tests |
| Tag-based markets have different `question` format | Med | Apply same `TRADY_AI_QUESTION_PATTERN`/`TRADY_AI_REJECT_PATTERNS` filters; operator sets patterns per domain |

## Rollback Plan

Revert to football-only: set `TRADY_AI_DOMAIN=FOOTBALL-WINNER` (default when unset). The league-based code path is preserved unchanged. If tag-based API changes, operator deletes `TRADY_AI_DISCOVERY_TAG_SLUG` and sets domain back to `FOOTBALL-WINNER` — zero code deploy needed.

## Dependencies

- `https://gamma-api.polymarket.com/events?tag_slug=` endpoint (already documented, used in production by Polymarket UI)

## Success Criteria

- [ ] `TRADY_AI_DOMAIN=CRYPTO-BINARY TRADY_AI_DISCOVERY_TAG_SLUG=crypto` discovers active crypto markets
- [ ] `TRADY_AI_DOMAIN=FOOTBALL-WINNER` (or unset) works identically to today
- [ ] 10 new tests pass; existing football tests unchanged
- [ ] `ensure_active_market.py` still <500 lines and standalone (no trady_ai imports)
