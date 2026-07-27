# Discovery Routing Specification

## Purpose

Domain-based routing that selects the correct discovery strategy. Both strategies produce identical output format: a single `condition_id` written to `.env`. The routing decision is a 1:1 domain→strategy mapping — deterministic by design.

*Ref: proposal §Approach item 4*

## Requirements

### REQ-DR-001: Deterministic Strategy Selection

The guard SHALL select the discovery strategy based on `TRADY_AI_DOMAIN`. Tag-based domains (e.g., `CRYPTO-BINARY`) MUST invoke `_discover_tag_based()`. League-based domains (e.g., `FOOTBALL-WINNER`) MUST invoke `_discover_league_based()`. Unknown domains MUST cause an immediate exit.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Tag-based route | `TRADY_AI_DOMAIN=CRYPTO-BINARY` | `main()` dispatches | calls `_discover_tag_based(tag_slug, question_pattern, reject_patterns)` |
| League-based route | `TRADY_AI_DOMAIN=FOOTBALL-WINNER` | `main()` dispatches | calls `_discover_league_based(leagues, winner_pattern, reject_patterns)` |
| Unknown domain | `TRADY_AI_DOMAIN=BASKETBALL` | `main()` dispatches | logs error listing valid domains (`FOOTBALL-WINNER, CRYPTO-BINARY`), exits 1 |

### REQ-DR-002: Unified Output Contract

Both discovery strategies SHALL produce the same output: a single `condition_id` written to `.env` under `TRADY_AI_ACTIVE_MARKETS`. The guard SHALL exit 0 on success (market found) and exit 1 on failure (no market), regardless of which strategy executed.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Tag-based success | `_discover_tag_based()` finds a valid market | discovery completes | writes `TRADY_AI_ACTIVE_MARKETS=<condition_id>` to `.env`, exits 0 |
| League-based success | `_discover_league_based()` finds a valid market | discovery completes | writes `TRADY_AI_ACTIVE_MARKETS=<condition_id>` to `.env`, exits 0 |
| Any strategy failure | either strategy finds no eligible market | discovery completes | exits 1, no `.env` mutation |

### REQ-DR-003: Existing League Logic Preservation

The `_discover_league_based()` path SHALL preserve the existing HTML scraping + slug resolution logic unchanged. When `TRADY_AI_DOMAIN=FOOTBALL-WINNER` (or defaulted), the guard's observable behavior — API calls, filter application, `.env` output — MUST be identical to the pre-refactor implementation.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Football identical | `TRADY_AI_DOMAIN=FOOTBALL-WINNER`, existing football `.env` config | guard runs | same HTTP calls, same eligibility checks, same `.env` output as current code |

---

**Boundary**: Routing is purely deterministic — domain identifier maps 1:1 to a strategy function. No dynamic selection, no confidence scoring, no intelligence. New domain support requires a code change (new `elif` branch), not a config change.
