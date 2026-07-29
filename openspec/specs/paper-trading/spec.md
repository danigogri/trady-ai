# Delta for Paper Trading

## ADDED Requirements

### REQ-PT-009: Discovery Clock [NEW]

Guard `scripts/ensure_active_market.py` — pre-session, stateless, deterministic. Reads `.env`, queries API per Condition ID, applies frozen rules, takes first valid, updates `.env`. Exit 0 if >=1 active; exit 1 if none. No ranking, no AI.

*Ref: SS6.1, S15, OC-2, AD-4*

- GIVEN all Condition IDs expired -> WHEN guard runs -> THEN queries `GET /markets`, filters rules, takes first valid, writes `.env`, logs `ROTATION`, exits 0
- GIVEN no candidates pass -> WHEN guard runs -> THEN exits 1, session blocked
- GIVEN >=1 active -> WHEN guard runs -> THEN exits 0, no mutation

### REQ-PT-010: Per-Clock Reconstruction [NEW]

Each clock tracks own progress: Discovery=`.env`, Evidence=`max_seq`, Decision=`last_processed_seq`, Reflection=`last_report_date`. Resume from first incomplete stage. MUST NOT use calendar day as sole granularity.

*Ref: AC-4, AD-8, S10*

- GIVEN `max_seq=450` after WS disconnect -> WHEN next session -> THEN Evidence resumes from seq 451
- GIVEN `last_processed_seq=400`, events to 500 -> WHEN next session -> THEN Decision processes `seq > 400` only

### REQ-PT-011: 15-Minute Execution Rhythm [NEW]

cron `*/15 * * * *` -> guard -> `trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive`. 60s capture. Target: 2,880 sessions/30d.

*Ref: OC-1, AD-9, S11*

- GIVEN cron fires at :00/:15/:30/:45, guard exits 0 -> WHEN triggered -> THEN session runs non-interactive, 60s capture

### REQ-PT-019: Calendar Day Computation [NEW]

The system SHALL compute the calendar day as `(date.today() - DAY_ZERO).days + 1` where DAY_ZERO is hardcoded as `date(2026, 7, 28)`. Calendar day progression SHALL be independent of session execution — skipped days advance the counter regardless. MUST NOT depend on DB state.

**Deterministic boundary**: Frozen DAY_ZERO constant; date arithmetic.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| First day | today = 2026-07-28 (DAY_ZERO) | `_compute_calendar_day()` | returns 1 |
| Next day | today = 2026-07-29 | `_compute_calendar_day()` | returns 2 |
| VPS down 2 days | today = 2026-08-05, DAY_ZERO = Jul 28 | session resumes | returns 9 (elapsed days), not session count |
| Midnight boundary | session 96 at 23:55, next at 00:05 | `_compute_calendar_day()` at 00:05 | returns next day's value |

### REQ-PT-020: Session Counter [NEW]

The system SHALL compute a session number by counting `reflection_reports` for the same domain where `DATE(created_at) = DATE('now')`, then adding 1. Session numbers SHALL be 1-indexed per domain, per calendar day.

**Deterministic boundary**: SQL COUNT of today's reports for the domain.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| First session | no reports for domain today | `_compute_session_number()` | returns 1 |
| Fourth session | 3 existing reports today | `_compute_session_number()` | returns 4 |
| Midnight reset | session 96 at 23:55 | `_compute_session_number()` at 00:05 | returns 1 (new day) |
| Empty DB | `reflection_reports` table empty | `_compute_session_number()` | returns 1 |

### REQ-PT-013: Backlog Integration [NEW]

All findings (bugs, violations, anomalies) as `BL-XXX` per Backlog Protocol. *Ref: S20.4*

- GIVEN CRITICAL violation -> WHEN bundle written -> THEN `BL-XXX` created

### REQ-PT-014: Daily DB Backup [NEW]

cron 02:00 UTC: `cp data/trady_ai.db data/backups/trady_ai-$(date +%Y%m%d).db`. *Ref: S5, S18.2*

- GIVEN 02:00 UTC -> WHEN cron fires -> THEN backup created

### REQ-PT-015: Calibration Evidence Bundles [NEW]

The system SHALL produce calibration evidence bundles as filesystem artifacts distinct
from session bundles. Directory: `paper_trading/cal-NNN/` where `cal-NNN` is a
UTC calendar day. Format: SHA-256 checksum manifest.

*Ref: RFC-004 §Paper Trading Operational Contract*

- GIVEN evidence report generated on 2026-07-20
- WHEN bundle is created
- THEN written to `paper_trading/cal-020/`, NOT `paper_trading/dia-020/`

### REQ-PT-016: Bundle Contents [NEW]

Each calibration bundle SHALL contain:
- `evidence_report-HHMMSS.json` — full EvidenceReport (AIC, BIC, χ², entropy, persistence)
- `adopted_config-HHMMSS.json` — {states, generator, evidence_ref, adopted_at, operator}
- `provenance-HHMMSS.json` — manifest with SHA-256 of both files, timestamp, hostname
- `manifest-HHMMSS.json` — bundle-level integrity checksum

`HHMMSS` timestamp suffix SHALL prevent overwrites from concurrent calibration runs.

- GIVEN `calibrate adopt` completed successfully
- WHEN bundle is written
- THEN directory contains evidence_report, adopted_config, provenance, and manifest
- AND manifest JSON includes SHA-256 of the other three files

### REQ-PT-017: Regenerability [NEW]

Bundles SHALL be regenerable from DB state: replaying the same DB at the same state SHALL
produce byte-identical bundle files. This REQUIRES deterministic JSON serialization
(`sort_keys=True`, fixed precision floats).

- GIVEN DB snapshot at adoption point and original bundle
- WHEN bundle regenerated from DB
- THEN SHA-256 of regenerated files matches original manifest checksums

### REQ-PT-018: Separation from Session Bundles [NEW]

Calibration bundles SHALL use the naming prefix `cal-NNN` and session bundles SHALL
continue using `dia-NNN`. No shared directory. A manifest validation that finds
calibration artifacts in `dia-NNN/` or session artifacts in `cal-NNN/` SHALL raise
a warning.

- GIVEN evidence_report.json accidentally in `dia-020/`
- WHEN manifest validation runs
- THEN warning raised: "Calibration artifact in session bundle directory"

## MODIFIED Requirements

### REQ-PT-001: Session Lifecycle [MODIFIED]

`PaperTradingSession` — stateless, `run_session() -> SessionReport`. Reconstruction uses per-clock sequence tracking (REQ-PT-010), not calendar day.

(Previously: reconstruction without per-clock sequence tracking)

| Transition | Validation |
|---|---|
| -> PRE_FLIGHT | Contracts + per-clock: Discovery `.env`, Evidence `max_seq`, Decision `last_processed_seq`, Reflection `last_report_date` |
| -> CAPTURING | DRY_RUN_ENFORCED, NO_REAL_FUNDS, DB ok |
| -> EXECUTING | >=1 new event since `last_processed_seq` |
| -> REFLECTING | ExecutionResult persisted |
| -> VERIFYING | reflection_report persisted |
| -> BUNDLING | Evidence completeness |
| -> COMPLETE | Manifest + checksums valid |

- GIVEN interrupted after EXECUTING -> WHEN next session -> THEN resumes at REFLECTING
- GIVEN full run -> WHEN `run_session("daily","FOOTBALL-WINNER",["0x123"])` -> THEN all states, SessionReport with `market_ids`

### REQ-PT-005: Evidence Bundling [MODIFIED]

`paper_trading/dia-NNN/sesion-MMM/` where `dia-NNN` = UTC calendar day (REQ-PT-019) and `sesion-MMM` = session number (REQ-PT-020). Each session writes to its own subdirectory. Files: `session_report.json`, `contracts.json`, `manifest.json`. Each includes `market_ids`. SHA-256 checksums in manifest. Session subdirectories replace HHMMSS filename suffixes.

(Previously: flat `dia-NNN/` with `HHMMSS` timestamp suffixes; no session subdirectories)

- GIVEN 96 sessions on Day 1 → WHEN all execute → THEN write to `dia-001/sesion-001/` through `dia-001/sesion-096/`, zero overwrites
- GIVEN Day 1 completed → WHEN next session on new calendar day → THEN writes to `dia-002/sesion-001/`

### REQ-PT-006: CLI Interface [MODIFIED]

`session --domain FOOTBALL-WINNER [--non-interactive] [--duration 60]`, `status`, `bundle`. `--non-interactive` suppresses prompts. `--duration` sets capture window. Output SHALL display "Day {N}, Session {M}".

(Previously: no `--non-interactive` or `--duration`; displayed "Day N" only)

- GIVEN `--non-interactive --duration 60`, day 1, session 4 → WHEN invoked → THEN output "Day 1, Session 4", no prompts, 60s capture, exit 0/1

### REQ-PT-007: Error Handling [MODIFIED]

Capture/Execute/Reflect fail -> ERROR, retryable with preserved state. Interrupted -> reconstruct per-clock (REQ-PT-010). Duplicate -> PRE_FLIGHT rejects.

(Previously: generic reconstruction without per-clock granularity)

- GIVEN reboot mid-session, `max_seq=450`, `last_processed_seq=400` -> WHEN cron resumes -> THEN Evidence from 451, Decision from 401

### REQ-PT-008: 30-Day Lifecycle [MODIFIED]

Day -1: FREEZE (rules, 5-10 Condition IDs, VPS, crontab). Day 0: pre-flight. Days 1-30: 15-min cycle using calendar days from frozen DAY_ZERO (`date(2026, 7, 28)`). Calendar day progression SHALL be independent of session execution. Day 30: >=30 reports → `ready_for_calibration`.

(Previously: daily cycle; no Day -1; day counter was session-based `COUNT(*)`)

- GIVEN DAY_ZERO = 2026-07-28, today = 2026-08-26 → WHEN day computation runs → THEN calendar day = 30 regardless of sessions executed
- GIVEN VPS down for days 5-7 (zero sessions) → WHEN VPS resumes → THEN calendar day = 8, preserving 30-day timeline

### REQ-PT-012: Session Report Audit Trail [MODIFIED]

`SessionReport` MUST include `market_ids: list[str]` and `session_number: int`. `SessionManifest` SHALL include `session_number`.

(Previously: only `market_ids`; no `session_number`)

- GIVEN third session of Day 1 for "FOOTBALL-WINNER" with `["0xABC","0xDEF"]` → WHEN report written → THEN `market_ids` present, `session_number = 3`

### REQ-PT-002: Operational Contracts [MODIFIED]

Validated in `contracts.py`. All existing contracts preserved. TEMPORAL_INTEGRITY refined from "no duplicate session today" to "no duplicate processing of the same event range" — with sub-daily execution, multiple sessions per day are expected and correct. Per-clock reconstruction (REQ-PT-010) already prevents re-processing the same events.

(Previously: TEMPORAL_INTEGRITY blocked all sessions after the first per calendar day)

| Contract | Validates | When | Severity | Change |
|---|---|---|---|---|
| DRY_RUN_ENFORCED | `validate_execution_secrets()` passes | PRE_FLIGHT | CRITICAL | None |
| NO_REAL_FUNDS | `place_order()` never called; trades dry_run=1 | PRE_FLIGHT + VERIFYING | CRITICAL | None |
| TEMPORAL_INTEGRITY | No duplicate processing of same event range (same domain, overlapping `last_processed_seq`) | PRE_FLIGHT | CRITICAL | **Refined**: per-seq, not per-day |
| EVIDENCE_COMPLETENESS | reflection_report exists | VERIFYING | CRITICAL | None |
| DETERMINISTIC_REPRODUCIBILITY | `verify_replay()` passes | VERIFYING | WARNING | None |
| REFLECTION_ISOLATION | Reflection writes only reflection tables | VERIFYING | CRITICAL | None |

*Ref: SS9.3, S10, AC-4*

## PRESERVED Requirements

| Req | Title | AC Ref |
|---|---|---|
| REQ-PT-003 | Operational Isolation | AC-3, S7.1 |
| REQ-PT-004 | Service Coordination | S6.1 |
