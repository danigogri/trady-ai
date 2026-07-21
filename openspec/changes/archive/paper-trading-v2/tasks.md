# Tasks: Paper Trading v2 — Architecture Contract Alignment

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~335 (additions + deletions) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Full v2 implementation | PR 1 | `pytest tests/paper_trading/ -v` | `trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive --duration 60` | Revert `paper_trading/` to Fase 5 archive, remove `scripts/ensure_active_market.py`, restore crontab |

## Phase 1: Discovery Clock — Guard Script

- [x] **T-001** `scripts/ensure_active_market.py` — Create standalone guard script (no trady_ai imports). Read `TRADY_AI_ACTIVE_MARKETS` from `.env`, query `GET /markets` per Condition ID, apply frozen eligibility rules, take first valid, write `.env`. Exit 0 if >=1 active; exit 1 if none. Log `ROTATION` on market change.
  - Dependencies: None
  - Files: `scripts/ensure_active_market.py` (new)
  - Spec: REQ-PT-009
  - Acceptance: `python scripts/ensure_active_market.py; echo $?` → 0 when markets active, 1 when none. `.env` updated on rotation.
  - Effort: M

## Phase 2: Config — Active Markets

- [x] **T-002** `src/trady_ai/config/settings.py` — Verify `TRADY_AI_ACTIVE_MARKETS` env var → `active_markets` field is read correctly via `get_active_market_ids()`. Confirm `Settings` re-reads `.env` per-process (no stale cache). No model changes needed — field already declared.
  - Dependencies: None
  - Files: `src/trady_ai/config/settings.py`
  - Spec: REQ-PT-009 (Discovery Clock), REQ-PT-006 (CLI)
  - Acceptance: `Settings().get_active_market_ids()` returns list from `.env`. Update `.env` between calls → next process sees new values.
  - Effort: S

## Phase 3: Data Model — SessionReport Audit Trail

- [x] **T-003** `src/trady_ai/paper_trading/models.py` — Add `market_ids: list[str] = field(default_factory=list)` field to `SessionReport` dataclass. No DB migration — field is runtime-only serialized into bundle JSON.
  - Dependencies: None
  - Files: `src/trady_ai/paper_trading/models.py`
  - Spec: REQ-PT-012
  - Acceptance: `SessionReport(day=1, domain="FW", event_count=0, trade_count=0, reflection_report_id=None, market_ids=["0xABC"])` stores and serializes `market_ids`.
  - Effort: S

## Phase 4: Session Reconstruction — Per-Clock Sequence Tracking

- [x] **T-004** `src/trady_ai/paper_trading/session.py` — Refactor `_reconstruct_stages()`. Replace `DATE(timestamp) = today` queries with per-clock sequence tracking:
  - **Discovery**: `.env` (guard-managed, checked at PRE_FLIGHT)
  - **Evidence**: `MAX(seq) FROM event_store WHERE domain = ?`
  - **Decision**: `last_processed_seq` from trades table
  - **Reflection**: `last_report_date` from reflection_reports
  - Also: wire `market_ids` into `run_session()` report construction. Pass `duration` parameter to `_do_capture()`.
  - Dependencies: T-003 (needs `market_ids` field)
  - Files: `src/trady_ai/paper_trading/session.py`
  - Spec: REQ-PT-001 (Session Lifecycle), REQ-PT-010 (Per-Clock Reconstruction), REQ-PT-007 (Error Handling)
  - Acceptance: Interrupt session after EXECUTING → next session resumes at REFLECTING. `max_seq=450` after disconnect → Evidence resumes from seq 451.
  - Effort: M

## Phase 5: Contracts — TEMPORAL_INTEGRITY Refinement

- [x] **T-005** `src/trady_ai/paper_trading/contracts.py` — Refine `temporal_integrity()` from per-calendar-day to per-sequence-overlap check. Change signature from `(db, day, domain)` to `(db, domain, last_processed_seq)`. Query: check no existing session processed events beyond `last_processed_seq` for same domain. Multiple sessions per calendar day are expected and valid under 15-min rhythm.
  - Dependencies: T-004 (needs per-clock contract to define `last_processed_seq`)
  - Files: `src/trady_ai/paper_trading/contracts.py`
  - Spec: REQ-PT-002 (TEMPORAL_INTEGRITY — refined)
  - Acceptance: Two sessions same day, non-overlapping seq → both pass. Two sessions same day, overlapping seq → second fails CRITICAL.
  - Effort: S

## Phase 6: Bundler — Concurrent-Write Protection

- [x] **T-006** `src/trady_ai/paper_trading/bundler.py` — Change bundle filenames from fixed `session_report.json`, `contracts.json`, `manifest.json` to `session_report-HHMMSS.json`, `contracts-HHMMSS.json`, `manifest-HHMMSS.json`. Use `datetime.now(UTC).strftime("%H%M%S")`. Include `market_ids` in serialized report. Day directory `dia-NNN/` unchanged.
  - Dependencies: T-003 (needs `market_ids` field)
  - Files: `src/trady_ai/paper_trading/bundler.py`
  - Spec: REQ-PT-005 (Evidence Bundling — modified)
  - Acceptance: 96 sessions on same day → all write to `dia-NNN/` with unique HHMMSS filenames, zero overwrites. Each JSON includes `market_ids`.
  - Effort: S

## Phase 7: CLI — Duration Flag

- [x] **T-007** `src/trady_ai/cli/main.py` — Add `--duration` option (type `int`, default 60) to `session` command. Pass it through to `PaperTradingSession.run_session()` as `duration` kwarg. Add `market_ids` to CLI output. `--non-interactive` flag already exists — no change needed.
  - Dependencies: T-004 (needs `run_session` accepting `duration`), T-001 (guard must exist for cron integration)
  - Files: `src/trady_ai/cli/main.py`
  - Spec: REQ-PT-006 (CLI Interface — modified), REQ-PT-011 (15-Minute Rhythm)
  - Acceptance: `trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive --duration 60` → no prompts, 60s capture, exit 0/1. Output includes market_ids.
  - Effort: M

## Phase 8: Testing — Guard, Reconstruction, Sub-Daily Execution

- [x] **T-008** `tests/paper_trading/test_guard.py` — Integration tests for guard script: (a) all Condition IDs active → exit 0, no mutation; (b) one expired → rotates, exits 0; (c) all expired, no candidates → exits 1; (d) `.env` mutation produces valid next-session read.
  - Dependencies: T-001
  - Files: `tests/paper_trading/test_guard.py` (new)
  - Spec: REQ-PT-009
  - Acceptance: `pytest tests/paper_trading/test_guard.py -v` → all 4 scenarios pass.
  - Effort: M

- [x] **T-009** `tests/paper_trading/test_reconstruction.py` — Integration tests for per-clock reconstruction: (a) interrupt after CAPTURING → next session skips CAPTURING; (b) interrupt after EXECUTING → resumes at REFLECTING; (c) `max_seq=450` → Evidence starts at 451; (d) `last_processed_seq=400` → Decision processes seq > 400 only.
  - Dependencies: T-004, T-005
  - Files: `tests/paper_trading/test_reconstruction.py` (new)
  - Spec: REQ-PT-001, REQ-PT-010, REQ-PT-007
  - Acceptance: `pytest tests/paper_trading/test_reconstruction.py -v` → all 4 scenarios pass.
  - Effort: M

- [x] **T-010** `tests/paper_trading/test_subdaily_execution.py` — Integration tests for 15-min rhythm: (a) 2 sessions same day → both complete with unique HHMMSS bundles; (b) TEMPORAL_INTEGRITY passes for non-overlapping seq; (c) `--duration 60` respect timed capture; (d) session report includes `market_ids`.
  - Dependencies: T-005, T-006, T-007
  - Files: `tests/paper_trading/test_subdaily_execution.py` (new)
  - Spec: REQ-PT-002, REQ-PT-005, REQ-PT-006, REQ-PT-011, REQ-PT-012
  - Acceptance: `pytest tests/paper_trading/test_subdaily_execution.py -v` → all 4 scenarios pass.
  - Effort: M

## Phase 9: Deployment — Crontab, Backup, Initial Config

- [x] **T-011** Deploy crontab: `*/15 * * * * cd /opt/trady && python scripts/ensure_active_market.py && trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive --duration 60`. Document VPS path and user in deployment notes.
  - Dependencies: T-001, T-007
  - Files: crontab entry (deployment artifact)
  - Spec: REQ-PT-011 (15-Minute Rhythm)
  - Acceptance: Crontab entry exists, guard-session chain tested manually on VPS.
  - Effort: S

- [x] **T-012** Deploy daily backup: `0 2 * * * cp /opt/trady/data/trady_ai.db /opt/trady/data/backups/trady_ai-$(date +%Y%m%d).db && sha256sum /opt/trady/data/backups/trady_ai-$(date +%Y%m%d).db > /opt/trady/data/backups/trady_ai-$(date +%Y%m%d).sha256`. Create `data/backups/` directory.
  - Dependencies: None
  - Files: crontab entry, `data/backups/` (new directory)
  - Spec: REQ-PT-014 (Daily DB Backup)
  - Acceptance: `data/backups/` exists. Manual run creates `trady_ai-YYYYMMDD.db` + `.sha256`.
  - Effort: S

- [x] **T-013** Initial `.env` configuration: Set `TRADY_AI_ACTIVE_MARKETS` with 5–10 Condition IDs for FOOTBALL-WINNER domain. Document in deployment runbook.
  - Dependencies: T-002
  - Files: `.env`
  - Spec: REQ-PT-009, REQ-PT-008 (Day -1 FREEZE)
  - Acceptance: `Settings().get_active_market_ids()` returns non-empty list matching `.env`.
  - Effort: S
