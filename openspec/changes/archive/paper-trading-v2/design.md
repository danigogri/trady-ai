# Design: Paper Trading v2 — Architecture Contract Alignment

## Technical Approach

This SDD cycle does NOT produce a standalone design. The **Paper Trading Architecture Contract v1.0** (frozen, 27 sections, 8 architectural reviews) IS the design. This document bridges spec requirements → Architecture Contract sections for traceability, and lists the implementation scope.

## Architecture Decisions

All 10 Accepted Architectural Decisions (AD-1 through AD-10, Contract §4) are frozen. This SDD implements them.

## Traceability Matrix

| Requirement | Title | Architecture Contract Ref | What It Governs |
|---|---|---|---|
| REQ-PT-001 | Session Lifecycle | §6.1 (Clock Definitions), §9.3 (Session Lifecycle), §10 (AC-4 Reconstruction) | Per-clock sequence tracking replaces calendar-day reconstruction |
| REQ-PT-002 | Operational Contracts | §7.1 (Bounded Contexts), §10 (AC-4) | TEMPORAL_INTEGRITY refined: per-seq not per-day |
| REQ-PT-003 | Operational Isolation | §7.1, §10 (AC-3 Clock Isolation) | Preserved — no import boundary changes |
| REQ-PT-004 | Service Coordination | §6.1, §8.1 (Dependency Graph) | Preserved — unidirectional DAG |
| REQ-PT-005 | Evidence Bundling | §5 (Output schema), §14.1 (Evidence Types) | HHMMSS timestamps for concurrent sessions; `market_ids` in artifacts |
| REQ-PT-006 | CLI Interface | §11 (OC-1 Execution Rhythm) | `--non-interactive`, `--duration` flags |
| REQ-PT-007 | Error Handling | §10 (AC-4), §20 (Failure Model) | Per-clock reconstruction on reboot/crash |
| REQ-PT-008 | 30-Day Lifecycle | §9.1 (Experiment Lifecycle), §17.2 (Calibration Gate) | 15-min rhythm, Day -1 FREEZE, Day 30 calibration gate |
| REQ-PT-009 | Discovery Clock | §6.1 (Discovery), §11 (OC-2 Evidence Continuity), §15 (Discovery Architecture), AD-4 | Guard script: stateless, first-valid, deterministic |
| REQ-PT-010 | Per-Clock Reconstruction | §10 (AC-4 Reconstruction Contract), AD-8 | Dispatch `.env` / `max_seq` / `last_processed_seq` / `last_report_date` per clock |
| REQ-PT-011 | 15-Minute Execution Rhythm | §11 (OC-1), AD-9 | cron → guard → session, 2,880 sessions/30d |
| REQ-PT-012 | Session Report Audit Trail | §5 (Output diagram), §25.3 (Day 0 Readiness) | `SessionReport.market_ids: list[str]` |
| REQ-PT-013 | Backlog Integration | §20.4 | Operational findings → `BL-XXX` per Backlog Protocol |
| REQ-PT-014 | Daily DB Backup | §5 (cron daily 02:00), §18.2 (Deployment) | `cp data/trady_ai.db data/backups/trady_ai-YYYYMMDD.db` |

## File Changes

| File | Action | Description |
|---|---|---|
| `scripts/ensure_active_market.py` | Create | Discovery Clock guard. Reads `.env`, queries API per Condition ID, applies frozen eligibility rules, takes first valid, updates `.env`. Exit 0 if >=1 active; exit 1 if none. |
| `src/trady_ai/paper_trading/session.py` | Modify | `_reconstruct_stages()`: per-clock sequence tracking (`.env`/`max_seq`/`last_processed_seq`/`last_report_date`) instead of `DATE(timestamp) = today`. `_do_capture()`: accept `duration` parameter for timed capture. |
| `src/trady_ai/paper_trading/models.py` | Modify | `SessionReport`: add `market_ids: list[str]` field (REQ-PT-012). |
| `src/trady_ai/paper_trading/contracts.py` | Modify | `temporal_integrity()`: refined to check per-seq overlap (`last_processed_seq`) instead of per-calendar-day — multiple sessions/day are expected under 15-min rhythm. |
| `src/trady_ai/paper_trading/bundler.py` | Modify | Bundle filenames: `session_report-HHMMSS.json`, `contracts-HHMMSS.json`, `manifest-HHMMSS.json` (REQ-PT-005). Prevents overwrite from 96 sessions/day. |
| `src/trady_ai/cli/main.py` | Modify | `session` command: add `--duration` option (default 60). `--non-interactive` already exists. Output includes `market_ids`. |
| `src/trady_ai/config/settings.py` | Modify | Ensure `TRADY_AI_ACTIVE_MARKETS` env var → `active_markets` field is read (already declared). Guard script will mutate `.env` between sessions; `Settings` re-reads per-process. |
| `crontab` (deployment) | Create | `*/15 * * * * guard && session --domain FOOTBALL-WINNER --non-interactive`. `0 2 * * * cp data/trady_ai.db data/backups/trady_ai-$(date +%Y%m%d).db`. |

## Design Principles

All 9 principles from Architecture Contract §3 apply unchanged:

| Principle | Contract § | Implementation Constraint |
|---|---|---|
| Deterministic-First | A1 | Guard: first-valid, no ranking. Reconstruction: per-seq. |
| Boundary Discipline | A3 | Guards MUST NOT cross clock boundaries (AC-3). |
| Fail-Fast | A4 | Guard exits 1 if no markets. Session ERROR if stage fails. |
| Simplicity Doctrine | A5 | 4 clocks, 1 guard, 1 crontab. Zero orchestration. |
| Governance Minimalism | A6 | Rules frozen in guard script; human owns `.env` override. |
| Validate Uncertainty First | A7 | 30-day experiment with full audit trail. |
| Evidence Before Complexity | A8 | SHA-256 manifest per session bundle. |
| Integration Hostility | B2 | SQLite + cron + Python stdlib. No cloud SDKs. |
| Human Sovereignty | RFC-007 | Guard applies frozen rules. Operator may edit `.env` directly at any time. |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The guard script invokes platform REST APIs (read-only GET), writes to a local `.env` file, and returns an exit code. No user-facing input vectors, no shell injection, no external process spawning.

## Migration / Rollout

No migration required. Existing `event_store`, `signals`, `trades`, and `reflection_reports` tables are preserved. The guard script, crontab, and per-clock reconstruction are additive. Rollback: revert `paper_trading/` to Fase 5 archive, remove guard, restore crontab.

## Open Questions

None — architecture is frozen.
