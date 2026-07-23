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

### REQ-PT-012: Session Report Audit Trail [NEW]

`SessionReport` MUST include `market_ids: list[str]`. *Ref: S5, S25.3*

- GIVEN session with `["0xABC","0xDEF"]` -> WHEN report written -> THEN `market_ids` present

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

`paper_trading/dia-NNN/` where `dia-NNN` = UTC calendar day, not session counter. Multiple sessions/day share the same day directory. Files within the directory use `HHMMSS` UTC timestamp suffix to prevent overwrites from concurrent sessions: `session_report-HHMMSS.json`, `contracts-HHMMSS.json`, `manifest-HHMMSS.json`. Each file includes `market_ids`. SHA-256 checksums in manifest.

(Previously: `dia-NNN` ambiguous; no `market_ids` field; no concurrent-write protection)

- GIVEN 96 sessions on 2026-07-20 -> WHEN execute -> THEN all write to `dia-020/` with unique `HHMMSS` filenames, zero overwrites

### REQ-PT-006: CLI Interface [MODIFIED]

`session --domain FOOTBALL-WINNER [--non-interactive] [--duration 60]`, `status`, `bundle`. `--non-interactive` suppresses prompts. `--duration` sets capture window.

(Previously: no `--non-interactive` or `--duration`)

- GIVEN `--non-interactive --duration 60` -> WHEN invoked -> THEN no prompts, 60s capture, exit 0/1

### REQ-PT-007: Error Handling [MODIFIED]

Capture/Execute/Reflect fail -> ERROR, retryable with preserved state. Interrupted -> reconstruct per-clock (REQ-PT-010). Duplicate -> PRE_FLIGHT rejects.

(Previously: generic reconstruction without per-clock granularity)

- GIVEN reboot mid-session, `max_seq=450`, `last_processed_seq=400` -> WHEN cron resumes -> THEN Evidence from 451, Decision from 401

### REQ-PT-008: 30-Day Lifecycle [MODIFIED]

Day -1: FREEZE (rules, 5-10 Condition IDs, VPS, crontab). Day 0: pre-flight. Days 1-30: 15-min cycle. Day 30: >=30 reports -> `ready_for_calibration`.

(Previously: daily cycle; no Day -1)

- GIVEN 30 days, >=30 reports -> THEN `calibration_state = "ready_for_calibration"`

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
