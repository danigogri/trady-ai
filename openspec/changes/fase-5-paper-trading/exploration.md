# Exploration: Fase 5 — Paper Trading (Operational Phase)

**Date**: 2026-07-12
**Change**: fase-5-paper-trading
**Phase**: Operational Validation (post-Fase 4, pre-Governance)
**Status**: Exploration complete — ready for proposal
**RFC lineage**: RFC-000 (Safety), RFC-004 (Reflection), Master Roadmap (Sequence D2)

---

## 1. Operational Lifecycle

### 30-Day Lifecycle

The Paper Trading period is a **bounded operational window** with three macro-phases:

```
DAY 0 (Start Gate)
├── Pre-flight checks (system health, config, credentials)
├── Calibration state = UNCALIBRATED (confirmed)
├── Event store: empty or reset (clean baseline)
└── Day counter = 0/30

DAY 1..30 (Operational Window)
├── Each day: capture → run → reflect (session scope)
├── Each day: verify artifacts persisted (completeness check)
├── Day 7, 14, 21, 28: weekly reflection (weekly scope)
└── Continuous: monitor for drift events, capture failures

DAY 30 (End Gate)
├── Final daily reflection
├── Calibration gate evaluation (time gate: 30 days, evidence gate: ≥30 sessions)
├── If gates pass → state transitions to READY_FOR_CALIBRATION
├── Operator reviews full evidence package
└── Governance decision: approve calibration → proceed to live, or extend/abort
```

### Day Lifecycle

Each operational day follows a deterministic sequence:

```
1. PRE-CHECK
   └── trady-ai status → verify: dry_run=true, execution_mode=dry_run, DB accessible

2. CAPTURE (continuous, hours-variable)
   └── trady-ai capture --markets <ids>
       ├── WS connects to Polymarket
       ├── Events persist to event_store (dedup by event_id)
       └── Operator stops with Ctrl+C (or daemon timeout)

3. EXECUTION (post-capture)
   └── trady-ai run --market <id> --since-seq <last_seq>
       ├── Engine consumes event_store → signals → decisions → trades
       ├── All trades have dry_run=1 (no real orders)
       └── Results persisted: signals, trades, execution_log, strategy_snapshots

4. REFLECTION (post-execution)
   └── trady-ai reflect analyze --scope session --domain PM-5M --mode dry_run
       ├── OutcomeAnalyzer → win_rate, PnL, drawdown
       ├── SignalQualityAnalyzer → accuracy, confidence calibration
       ├── DriftAnalyzer → transition matrix comparison
       ├── ProposalGenerator → bounded parameter proposals (if drift detected)
       └── Report persisted to reflection_reports

5. ARTIFACT VERIFICATION
   └── trady-ai reflect report --domain PM-5M
       ├── Confirm report persisted for today
       ├── Check drift_events count
       └── Check proposals count
```

### Start Gate (Day 0 Preconditions)

| Check | Mechanism | Pass Criteria |
|-------|-----------|---------------|
| execution_mode | `trady-ai status` | `dry_run` |
| DB accessible | `trady-ai status` | event_store count shown |
| Polymarket WS | `trady-ai capture --markets <id>` (5s test) | Events captured |
| Reflection works | `trady-ai reflect analyze --scope session` | Report generated (may be empty) |
| Calibration state | Query `reflection_config` | `uncalibrated` |
| No real funds at risk | `validate_execution_secrets()` | Passes in dry_run (no-op) |

### End Gate (Day 30 Exit Criteria)

| Criterion | Mechanism | Threshold |
|-----------|-----------|-----------|
| Time gate | `COUNT(DISTINCT DATE(period_start))` from `reflection_reports` | ≥ 30 |
| Evidence gate | `COUNT(*)` from `reflection_reports` WHERE domain = 'PM-5M' | ≥ 30 (min_sessions) |
| All trades dry_run | `SELECT COUNT(*) FROM trades WHERE dry_run=0` | 0 |
| No unresolved capture failures | Operator log review | 0 critical gaps |

---

## 2. Session Lifecycle

### Session Definition

A Paper Trading **session** is one complete capture → run → reflect cycle. It is the atomic operational unit.

```
Session States:
  IDLE → CAPTURING → EXECUTING → REFLECTING → COMPLETE
                                    ↓
                              (failure at any point)
                                    ↓
                                 FAILED
```

| State | Entry Condition | Exit Condition | Operator Action |
|-------|----------------|----------------|-----------------|
| IDLE | Session not started | Operator starts capture | `trady-ai capture` |
| CAPTURING | WS connected, events flowing | Operator stops capture (Ctrl+C) | Monitor, stop when sufficient |
| EXECUTING | Capture stopped, events in store | Engine run completes | `trady-ai run` |
| REFLECTING | Execution complete | Reflection report persisted | `trady-ai reflect analyze` |
| COMPLETE | Report persisted, artifacts verified | — | Verify artifacts, log day |
| FAILED | Any step throws exception | Operator diagnoses | Retry or skip (document gap) |

### How the Operator Knows a Session is Complete

1. `trady-ai reflect report --domain PM-5M` shows a report with today's date
2. `trady-ai status` shows updated event count
3. No unhandled exceptions in terminal output

### Session Frequency

- **Minimum**: 1 session per day (to satisfy the time gate: 30 distinct calendar days)
- **Maximum**: Multiple sessions per day allowed (contributes to evidence gate)
- **Recommended**: 1-3 sessions per day depending on market activity

---

## 3. Operational Contracts

These invariants MUST hold for the Paper Trading period to produce valid evidence:

### C1: Dry-Run Enforcement
- ALL trades MUST have `dry_run=1`
- `execution_mode` MUST remain `dry_run` for the entire 30-day period
- `validate_execution_secrets()` MUST pass before each `run` and `capture`
- **Violation**: Any `dry_run=0` trade invalidates the Paper Trading period

### C2: Evidence Completeness
- Every session MUST produce: ≥1 reflection_report row, ≥0 drift_events, ≥0 proposals
- Every capture MUST persist events to `event_store` with `raw_payload NOT NULL`
- Every run MUST persist signals, execution_log entries, and trades
- **Violation**: Missing artifacts for a day = gap in evidence (documented, day may not count)

### C3: Deterministic Reproducibility
- Same event_store content + same strategy parameters → same signals, trades, reports
- Replay verification (`replay()` + `verify_replay()`) SHOULD pass after each run
- **Violation**: Non-deterministic output indicates a bug, not a market signal

### C4: Reflection Isolation
- Reflection MUST NOT mutate Core tables (signals, trades, positions, execution_log)
- Reflection writes ONLY to: reflection_reports, drift_events, proposals, reflection_config
- **Violation**: Core table mutation by Reflection = architectural breach (RFC-004)

### C5: No Real Funds
- Polymarket API key MAY be present (for data access) but MUST NOT be used for order placement
- `place_order()` MUST NOT be called during Paper Trading
- **Violation**: Any real order = critical safety incident (RFC-000)

### C6: Temporal Integrity
- Each reflection report's `period_start`/`period_end` MUST reflect actual analysis window
- 30 distinct calendar days MUST have reports (time gate)
- **Violation**: Backdated reports = evidence fraud (operator integrity)

---

## 4. Required Artifacts

### Per Session

| Artifact | Table | Produced By | Verified By |
|----------|-------|-------------|-------------|
| Raw market events | `event_store` | `capture` (EventCapture) | `trady-ai status` (event count) |
| Signals | `signals` | `run` (ExecutionEngine) | `trady-ai analyze --market <id>` |
| Execution log | `execution_log` | `run` (ExecutionEngine) | Row count in DB |
| Trades (dry_run=1) | `trades` | `run` (ExecutionEngine) | `SELECT COUNT(*) FROM trades WHERE dry_run=1` |
| Strategy snapshots | `strategy_snapshots` | `run` (MarkovPersistenceEngine) | Latest snapshot exists |
| Reflection report | `reflection_reports` | `reflect analyze` | `trady-ai reflect report` |
| Drift events (if any) | `drift_events` | `reflect analyze` | Report shows drift alerts |
| Proposals (if any) | `proposals` | `reflect analyze` | Report shows proposals |

### Per Day

| Artifact | Source | Purpose |
|----------|--------|---------|
| ≥1 reflection_report | `reflect analyze --scope session` | Evidence for time gate |
| Operator log entry (manual) | Notebook/spreadsheet | Track day N/30, anomalies, market conditions |
| Capture duration + event count | Terminal output | Verify sufficient data captured |

### Per 30-Day Period (Aggregate)

| Artifact | Source | Purpose |
|----------|--------|---------|
| 30+ reflection_reports | `reflection_reports` table | Time gate + evidence gate |
| Drift event history | `drift_events` table | Stability analysis |
| All proposals (draft) | `proposals` table | Governance review input |
| Calibration state transition | `reflection_config` | `ready_for_calibration` |
| Full evidence package | DB backup (`.db` file) | Governance audit trail |
| Operator notebook | External document | Context, anomalies, market regime notes |

---

## 5. Operator Responsibilities (Human + OpenCode)

### Pre-Flight (Day 0)

- [ ] Verify `execution_mode=dry_run` in config
- [ ] Run `trady-ai status` — confirm system healthy
- [ ] Test capture with 10s WS connection
- [ ] Test `trady-ai reflect analyze` — confirm reflection pipeline works
- [ ] Confirm calibration_state = `uncalibrated`
- [ ] Set up operator notebook (day tracking)

### Daily Checklist (Days 1-30)

- [ ] Run `trady-ai status` — pre-check
- [ ] Start capture: `trady-ai capture --markets <ids>`
- [ ] Monitor capture (watch for WS disconnects, errors)
- [ ] Stop capture after sufficient data (market hours dependent)
- [ ] Run engine: `trady-ai run --market <id> --since-seq <last_seq>`
- [ ] Review execution output (signals, trades, PnL)
- [ ] Run reflection: `trady-ai reflect analyze --scope session --domain PM-5M`
- [ ] Verify report: `trady-ai reflect report --domain PM-5M`
- [ ] Log day number, event count, trade count, drift alerts in notebook
- [ ] On day 7/14/21/28: also run `trady-ai reflect analyze --scope weekly`

### Weekly Review (Days 7, 14, 21, 28)

- [ ] Run weekly reflection
- [ ] Review drift trends across the week
- [ ] Review any proposals generated
- [ ] Note market regime observations in notebook
- [ ] Verify all daily reports exist for the week

### End-of-Period (Day 30)

- [ ] Run final daily reflection
- [ ] Verify time gate: `SELECT COUNT(DISTINCT DATE(period_start)) FROM reflection_reports WHERE domain='PM-5M'` ≥ 30
- [ ] Verify evidence gate: `SELECT COUNT(*) FROM reflection_reports WHERE domain='PM-5M'` ≥ 30
- [ ] Verify no live trades: `SELECT COUNT(*) FROM trades WHERE dry_run=0` = 0
- [ ] Export DB backup as evidence package
- [ ] Compile operator summary: win_rate trends, drift patterns, proposal history
- [ ] Present evidence to Governance (manual review, Fase 7 will formalize)

### Interruption Handling

| Scenario | Action |
|----------|--------|
| Capture fails mid-session | Log gap, restart capture. Day still counts if reflection runs on available data |
| Engine run fails | Check event_store integrity, retry. If unrecoverable, day may not count |
| Reflection fails | Check DB integrity, retry. Report MUST exist for day to count |
| Multiple days missed | Extend 30-day window by number of missed days (time gate still requires 30 distinct days) |
| DB corruption | Restore from backup. If no backup, Paper Trading period restarts |

---

## 6. OpenCode Responsibilities

OpenCode (the AI assistant) serves as the operator's technical assistant during each session:

### Per Session

- [ ] Execute CLI commands on behalf of the operator (capture, run, reflect)
- [ ] Monitor command output for errors or anomalies
- [ ] Verify artifact persistence (query DB to confirm rows exist)
- [ ] Run replay verification after engine runs
- [ ] Format and present reflection results in readable summary
- [ ] Flag drift alerts or unusual patterns

### Per Day

- [ ] Confirm all daily checklist items completed
- [ ] Summarize day's results: events captured, trades executed, PnL, drift status
- [ ] Update operator notebook with structured data
- [ ] Alert if any contract violation detected (e.g., dry_run=0 trade)

### Per Week

- [ ] Generate weekly summary: trends in win_rate, PnL, signal accuracy
- [ ] Compare weekly reflection vs. session reflections
- [ ] Highlight any drift trends or proposal patterns
- [ ] Verify all daily artifacts exist for the week

### End-of-Period

- [ ] Generate comprehensive evidence summary
- [ ] Verify all gates pass (time, evidence, dry_run)
- [ ] Compile proposal package for Governance review
- [ ] Produce operator-friendly report of 30-day performance

---

## 7. Future: Hermes Responsibilities

> **NOTE**: This section describes FUTURE evolution only. Hermes does NOT exist in the current system. These are capabilities that Hermes MAY assume in post-Paper-Trading phases.

### What Hermes Would Automate (Post-Paper-Trading)

| Current Manual Step | Hermes Future Capability |
|---------------------|--------------------------|
| Operator starts/stops capture | Hermes schedules capture windows based on market hours |
| Operator triggers run | Hermes auto-runs engine after capture completes |
| Operator triggers reflection | Hermes auto-triggers session reflection post-execution |
| Operator verifies artifacts | Hermes runs completeness checks automatically |
| Operator logs daily summary | Hermes generates and persists daily summary |
| Operator monitors for errors | Hermes detects failures and alerts/retries |
| Operator tracks day N/30 | Hermes maintains session counter and progress |
| Weekly reflection trigger | Hermes auto-triggers weekly scope on day boundaries |
| End-of-period gate check | Hermes evaluates calibration gates and notifies operator |

### What Hermes MUST NOT Do (Even in Future)

- Approve or reject proposals (Governance authority, RFC-004)
- Mutate production parameters without Governance approval
- Switch execution_mode from dry_run to live
- Bypass or override calibration gates
- Make trading decisions

### Transition Criteria (Human → Hermes)

Hermes automation should only begin after:
1. Paper Trading completes successfully (30 days, gates pass)
2. Governance reviews and approves Hermes automation scope
3. Hermes operates under explicit bounded authority (Fase 8 — Autonomous Coordination)

---

## 8. Open Questions Before Proposal

### Q1: Does Paper Trading require new code?

**Analysis**: The core operations (capture, run, reflect) already exist as CLI commands. The calibration gate logic already exists in `ReflectionEngine._check_calibration_readiness()`. What's potentially missing:

- **Option A — No new code**: Operator runs existing commands manually for 30 days. Document the procedure. The system already produces all required artifacts.
- **Option B — Minimal orchestration**: Add a `trady-ai paper-trade` CLI command that wraps the daily cycle (capture → run → reflect → verify) with progress tracking (day N/30, artifact completeness).
- **Option C — Session tracker**: Add a `paper_trading_sessions` table to track session lifecycle (start, end, status, day_number) for auditability.

**Leaning**: Option A or B. Option C may be overengineering for a 30-day manual period.

### Q2: What constitutes a "sufficient" daily capture?

The system has no minimum event count or capture duration threshold. Should there be a minimum number of events per day for the day to count toward the time gate?

**Possible answer**: Define a minimum (e.g., ≥100 events/day) as a soft guideline, not a hard gate. Operator judgment for now; formalize in Governance (Fase 7).

### Q3: How to handle market closures / low-activity days?

Polymarket prediction markets may have low activity on weekends or holidays. Should these days count?

**Possible answer**: Yes, they count if capture + run + reflect complete successfully. Low activity is itself valuable evidence (system handles low-volume regimes).

### Q4: Should replay verification be mandatory per session?

`replay()` + `verify_replay()` exists but is only invoked in the `backtest` CLI command, not in `run`. Should Paper Trading require replay verification after every session?

**Possible answer**: Yes, add replay verification to the daily checklist. If replay fails, it indicates a determinism bug that must be investigated before continuing.

### Q5: What is the "evidence package" format for Governance?

When the 30 days complete, what does the operator present to Governance? Just the DB file? A structured report?

**Possible answer**: DB file + operator summary document + reflection report aggregate. Formalize the evidence package structure in the Proposal.

### Q6: Does the `since_seq` parameter need automation?

Currently, `trady-ai run --since-seq <N>` requires the operator to know the last processed seq. Should the system track this automatically?

**Possible answer**: The operator can use `trady-ai status` to see `last seq` and pass it. For 30 days of manual operation, this is acceptable. Hermes would automate this later.

### Q7: Should the 30-day clock start from Day 0 (pre-flight) or Day 1 (first session)?

**Possible answer**: Day 1 = first successful complete session (capture → run → reflect). Day 0 is preparation.

---

## 9. Recommended SDD Scope

### Assessment

Paper Trading is primarily an **operational phase**, not a feature development phase. The system already has all the technical capabilities required:

- ✅ Market data capture (Polymarket WS)
- ✅ Deterministic execution engine (dry_run mode)
- ✅ Reflection analysis (session/daily/weekly scopes)
- ✅ Calibration gate (30-day time gate + evidence gate)
- ✅ Evidence persistence (all required tables exist)
- ✅ CLI interface for all operations

### Recommended Scope: **Operational SDD with Minimal Code Additions**

The SDD should deliver:

1. **Operational Procedure Document** (primary deliverable)
   - Day-by-day operator checklist
   - Session lifecycle definition
   - Interruption handling procedures
   - End-of-period gate verification
   - Evidence package specification

2. **Optional: `paper-trade` CLI command** (if Option B from Q1 is chosen)
   - Wraps daily cycle: capture → run → reflect → verify
   - Shows progress: day N/30, sessions completed, artifacts status
   - Does NOT replace individual commands (they remain usable independently)
   - Survives into production as a convenience orchestration layer

3. **Optional: Session tracking** (if auditability demands it)
   - `paper_trading_sessions` table: session_id, day_number, started_at, completed_at, status, event_count, trade_count, report_id
   - Provides queryable audit trail for Governance

### What the SDD Should NOT Do

- ❌ Build new analyzers or reflection capabilities (Fase 4 already did this)
- ❌ Modify the execution engine or pipeline
- ❌ Add intelligence/LLM integration (that's Fase 5 proper)
- ❌ Build governance automation (that's Fase 7)
- ❌ Create temporary scripts that won't survive into production

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Operator misses a day | Low | Time gate requires 30 DISTINCT days, not 30 consecutive. Missed days extend the calendar. |
| DB corruption | Medium | Daily DB backup as part of procedure. SQLite is file-based, easy to copy. |
| WS capture fails silently | Medium | Event count check per session. Zero events = alert. |
| dry_run accidentally switched to live | Critical | Config check in pre-flight. `validate_execution_secrets()` gates execution. |
| Evidence insufficient for Governance | Low | Evidence gate (min_sessions=30) ensures sufficient data. Operator monitors progress. |

---

## Affected Areas

- `src/trady_ai/cli/main.py` — may gain `paper-trade` command (optional)
- `src/trady_ai/core/persistence.py` — may gain session tracking table (optional)
- `openspec/specs/paper-trading/` — new spec directory (operational contract)
- `openspec/changes/fase-5-paper-trading/` — SDD artifacts
- No changes to: engine.py, reflection/, adapters/, strategies/, config/

---

## Ready for Proposal

**Yes** — exploration is complete. The orchestrator should:

1. Review the 7 open questions with the user (especially Q1: code vs. operational-only)
2. Decide on scope: Option A (pure ops), Option B (minimal CLI), or Option C (session tracking)
3. Launch SDD proposal phase (sdd-propose) for fase-5-paper-trading
4. Proposal should reference RFC-000, RFC-004, Master Roadmap sequence, and BL-019

**Key insight**: This is fundamentally an operational milestone, not a feature build. The SDD should be lightweight — primarily a structured operational procedure with optional minimal tooling. The system already works; the goal is to operate it with discipline for 30 days and produce auditable evidence for Governance.
