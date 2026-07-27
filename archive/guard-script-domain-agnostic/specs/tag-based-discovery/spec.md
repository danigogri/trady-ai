# Tag-Based Discovery Specification

## Purpose

API-driven market discovery for tag-based domains (e.g., crypto). Replaces the league-based HTML scraping path with a single gamma-api call. Frozen rules (question pattern, reject patterns, CLOB verification) remain identical — only the *discovery transport* differs.

*Ref: proposal §Approach item 3; RFC-006 §Domain Isolation*

## Requirements

### REQ-TD-001: Single API Discovery

The guard SHALL discover markets via a single request to `GET https://gamma-api.polymarket.com/events?tag_slug={slug}&active=true&closed=false&limit=50`. The response contains events with embedded markets. The guard SHALL extract `condition_id` from the first valid market.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Markets returned | API returns events with embedded markets | guard calls API | extracts `condition_id` from first `active=true, closed=false` market |
| Empty response | API returns `[]` or events with no markets | guard calls API | logs "no markets found", exits 1 |

### REQ-TD-002: Frozen Filter Application

The guard SHALL apply `TRADY_AI_QUESTION_PATTERN` (regex match) and `TRADY_AI_REJECT_PATTERNS` (substring match) to every market's `question` field. Only markets passing both filters are eligible. When `TRADY_AI_QUESTION_PATTERN` is absent, the guard SHALL use a sensible domain default.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Question matches | question matches `TRADY_AI_QUESTION_PATTERN` regex, no reject hit | filter applied | market is eligible |
| Pattern mismatch | question does not match regex | filter applied | market skipped |
| Reject hit | question contains a reject pattern substring | filter applied | market skipped |

### REQ-TD-003: CLOB Verification

After discovering an eligible market, the guard SHALL verify it via `GET clob.polymarket.com/markets/{condition_id}`. Only markets with `active==true` and `closed==false` are accepted. This is the same double-check used by the league-based path.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| CLOB confirms active | `active: true, closed: false` | CLOB queried | market accepted, `condition_id` written to `.env` |
| CLOB rejects | `active: false` or `closed: true` | CLOB queried | market skipped, next candidate tried |

### REQ-TD-004: Error Handling

API failures SHALL produce a structured log entry and non-zero exit (1). Connection errors (including Cloudflare blocks) SHALL be surfaced as distinct log entries to aid operator diagnosis.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Non-200 HTTP | gamma-api returns 4xx/5xx | guard calls API | logs `http_get_failed` with url and status, exits 1 |
| Connection error | TCP connect/reset failure (e.g., Cloudflare block) | guard calls API | logs connection error distinctly, exits 1 |
| JSON decode failure | response body is not valid JSON | guard calls API | logs parse error, exits 1 |

---

**Boundary**: Fully deterministic. Same `tag_slug` + same API state → same `condition_id`. No ranking, no AI, no scoring. Discovery transport is the only variable; frozen eligibility rules are shared across strategies.
