# Tasks: Guard Script Domain-Agnostic Discovery

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 250–300 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Configuration Foundation

- [x] 1.1 RED: Add `test_domain_default_to_football`, `test_domain_explicit_crypto`, `test_domain_invalid_exits` to `TestLoadDiscoveryConfig` in `tests/unit/test_ensure_active_market.py` [DC-001]
- [x] 1.2 RED: Add `test_tag_slug_required_for_crypto`, `test_tag_slug_empty_exits`, `test_tag_slug_ignored_for_football` to `TestLoadDiscoveryConfig` [DC-002]
- [x] 1.3 RED: Add `test_legacy_vars_still_read` and `test_deprecation_warning_logged_when_domain_unset` to `TestLoadDiscoveryConfig` [DC-003]
- [x] 1.4 GREEN: Refactor `_load_discovery_config()` at `scripts/ensure_active_market.py:178-227`: read `TRADY_AI_DOMAIN` (default `FOOTBALL-WINNER`), `TRADY_AI_DISCOVERY_TAG_SLUG`; validate domain ∈ `{FOOTBALL-WINNER, CRYPTO-BINARY}` (invalid → log + exit 1); enforce non-empty tag_slug for tag-based domains [DC-001, DC-002, DC-003]; log deprecation warning when legacy vars present without explicit domain [DC-003]; return dict adds `domain: str`, `tag_slug: str | None`, renames `winner_pattern`→`question_pattern`
- [x] 1.5 GREEN: Add `## Domain Configuration` section to `.env.example` documenting `TRADY_AI_DOMAIN`, `TRADY_AI_DISCOVERY_TAG_SLUG`, `TRADY_AI_QUESTION_PATTERN`

## Phase 2: Core Discovery Logic

- [x] 2.1 GREEN: Rename `_DEFAULT_WINNER_PATTERN`→`_DEFAULT_QUESTION_PATTERN` (line 70), `_is_winner_market()`→`_is_eligible_market()` (line 299), local `winner_pattern`→`question_pattern` cascade through `_find_eligible_market()`, `TestIsWinnerMarket`, `TestMainFlow` [DR-003]
- [x] 2.2 RED: Add `TestDiscoverTagBased` class in `tests/unit/test_ensure_active_market.py` with mocked `_http_get_json` + `_query_market_active`: success extracts `condition_id` [TD-001], filter rejects non-matching/rejected questions [TD-002], CLOB confirms/filters [TD-003], error paths (non-200, empty `[]`, JSON decode, URLError) [TD-004]
- [x] 2.3 GREEN: Implement `_discover_tag_based(tag_slug, question_pattern, reject_patterns) → str | None` (~50 lines) after `_load_discovery_config()`: `GET /events?tag_slug=&active=true&closed=false&limit=50`, walk event markets, apply `_is_eligible_market()`, pass first through `_query_market_active()` [TD-001–TD-004]
- [x] 2.4 RED: Add `test_tag_based_domain_discovers_and_writes`, `test_tag_based_no_market_exits_1`, `test_league_based_unchanged` to `TestMainFlow` mocking discovery strategies [DR-001, DR-002, DR-003]
- [x] 2.5 GREEN: Wire domain routing in `main()` at `scripts/ensure_active_market.py:357-436`: destructure `domain`/`tag_slug` from config; in both Phase 2 rotation branches, `if domain == "CRYPTO-BINARY"` → `_discover_tag_based()` else → existing league loop with `_find_eligible_market()` [DR-001, DR-002]

## Phase 3: Regression & Verify

- [x] 3.1 GREEN: Update all remaining `winner_pattern`→`question_pattern` references in `TestLoadDiscoveryConfig` setup, `TestMainFlow` mocks, and test assertions [DR-003]
- [x] 3.2 Verify: `pytest tests/unit/test_ensure_active_market.py -v` — all existing tests pass unchanged; 21+ new tests pass
- [x] 3.3 Verify: Run `python scripts/ensure_active_market.py` with `TRADY_AI_DOMAIN=FOOTBALL-WINNER` using existing `.env` — identical behavior to pre-refactor [DR-003]
