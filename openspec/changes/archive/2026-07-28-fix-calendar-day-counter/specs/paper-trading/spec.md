# Delta for Paper Trading

## ADDED Requirements

### REQ-PT-019: Calendar Day Computation

The system SHALL compute the calendar day as `(date.today() - DAY_ZERO).days + 1` where DAY_ZERO is hardcoded as `date(2026, 7, 28)`. Calendar day progression SHALL be independent of session execution — skipped days advance the counter regardless. MUST NOT depend on DB state.

**Deterministic boundary**: Frozen DAY_ZERO constant; date arithmetic.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| First day | today = 2026-07-28 (DAY_ZERO) | `_compute_calendar_day()` | returns 1 |
| Next day | today = 2026-07-29 | `_compute_calendar_day()` | returns 2 |
| VPS down 2 days | today = 2026-08-05, DAY_ZERO = Jul 28 | session resumes | returns 9 (elapsed days), not session count |
| Midnight boundary | session 96 at 23:55, next at 00:05 | `_compute_calendar_day()` at 00:05 | returns next day's value |

### REQ-PT-020: Session Counter

The system SHALL compute a session number by counting `reflection_reports` for the same domain where `DATE(created_at) = DATE('now')`, then adding 1. Session numbers SHALL be 1-indexed per domain, per calendar day.

**Deterministic boundary**: SQL COUNT of today's reports for the domain.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| First session | no reports for domain today | `_compute_session_number()` | returns 1 |
| Fourth session | 3 existing reports today | `_compute_session_number()` | returns 4 |
| Midnight reset | session 96 at 23:55 | `_compute_session_number()` at 00:05 | returns 1 (new day) |
| Empty DB | `reflection_reports` table empty | `_compute_session_number()` | returns 1 |

## MODIFIED Requirements

### REQ-PT-005: Evidence Bundling

`paper_trading/dia-NNN/sesion-MMM/` where `dia-NNN` = UTC calendar day (REQ-PT-019) and `sesion-MMM` = session number (REQ-PT-020). Each session writes to its own subdirectory. Files: `session_report.json`, `contracts.json`, `manifest.json`. Each includes `market_ids`. SHA-256 checksums in manifest. Session subdirectories replace HHMMSS filename suffixes.

(Previously: flat `dia-NNN/` with `HHMMSS` timestamp suffixes; no session subdirectories)

- GIVEN 96 sessions on Day 1 → WHEN all execute → THEN write to `dia-001/sesion-001/` through `dia-001/sesion-096/`, zero overwrites
- GIVEN Day 1 completed → WHEN next session on new calendar day → THEN writes to `dia-002/sesion-001/`

### REQ-PT-006: CLI Interface

`session --domain FOOTBALL-WINNER [--non-interactive] [--duration 60]`, `status`, `bundle`. `--non-interactive` suppresses prompts. `--duration` sets capture window. Output SHALL display "Day {N}, Session {M}".

(Previously: no `--non-interactive` or `--duration`; displayed "Day N" only)

- GIVEN `--non-interactive --duration 60`, day 1, session 4 → WHEN invoked → THEN output "Day 1, Session 4", no prompts, 60s capture, exit 0/1

### REQ-PT-008: 30-Day Lifecycle

Day -1: FREEZE (rules, 5-10 Condition IDs, VPS, crontab). Day 0: pre-flight. Days 1-30: 15-min cycle using calendar days from frozen DAY_ZERO (`date(2026, 7, 28)`). Calendar day progression SHALL be independent of session execution. Day 30: >=30 reports → `ready_for_calibration`.

(Previously: daily cycle; no Day -1; day counter was session-based `COUNT(*)`)

- GIVEN DAY_ZERO = 2026-07-28, today = 2026-08-26 → WHEN day computation runs → THEN calendar day = 30 regardless of sessions executed
- GIVEN VPS down for days 5-7 (zero sessions) → WHEN VPS resumes → THEN calendar day = 8, preserving 30-day timeline

### REQ-PT-012: Session Report Audit Trail

`SessionReport` MUST include `market_ids: list[str]` and `session_number: int`. `SessionManifest` SHALL include `session_number`.

(Previously: only `market_ids`; no `session_number`)

- GIVEN third session of Day 1 for "FOOTBALL-WINNER" with `["0xABC","0xDEF"]` → WHEN report written → THEN `market_ids` present, `session_number = 3`
