# Paper Trading Architecture Contract

**Status:** PERMANENTLY FROZEN — Review cycle closed. All 13 documentation observations resolved.
**Authority Level:** Architecture (binding for all Paper Trading SDD cycles, implementation, review, and audit)
**Version:** 1.0
**Date Frozen:** July 2026
**Derives Authority From:** PORTABLE-OS-CONSTITUTION.md, RFC-000 through RFC-009, TRADY-AI-MASTER-ROADMAP-001
**Associated Reviews:** 8 architectural reviews + 3 documentation reviews — all resolved and archived

---

## 1. Executive Summary

Paper Trading is a 30-day operational experiment designed to calibrate Trady AI's deterministic execution pipeline against real market data. Its primary asset is evidence, not profit.

The architecture is organized around four independent operational clocks — Discovery, Evidence, Decision, and Reflection — with strictly unidirectional dependencies. Each clock owns a single bounded responsibility and executes at its natural temporal rhythm.

The experiment runs continuously on a Linux VPS, scheduled via cron at 15-minute intervals. A deterministic guard script preserves evidence continuity by rotating expired markets under frozen rules defined by the human operator. All trading decisions remain inside the deterministic pipeline. Hermes and other intelligence systems are excluded from the operational critical path.

After 30 days, the accumulated evidence — 2,880 sessions, each with full audit trail — enables the Reflection Engine to determine calibration readiness and inform future governance decisions.

---

## 2. Architectural Scope

### 2.1 What This Architecture Governs

| Scope | Description |
|---|---|
| Operational lifecycle of one 30-day paper trading campaign | Discovery → Evidence → Decision → Reflection cycle |
| Market selection and rotation policies | Deterministic rules for maintaining active markets |
| Evidence collection, persistence, and audit | Data integrity and traceability guarantees |
| Human governance boundaries | What the operator decides vs what the pipeline executes |
| Failure detection and recovery | Per-clock state reconstruction |
| Infrastructure portability | Runtime, storage, and scheduling contracts |

### 2.2 What This Architecture Does NOT Govern

| Out of Scope | Governed By |
|---|---|
| Strategy implementation | RFC-003, Strategy Infrastructure SDD |
| Intelligence integration (Hermes, models) | RFC-005, Intelligence Integration SDD |
| Autonomous coordination | RFC-008 (deferred to Phase 8) |
| Multi-domain expansion | RFC-006 (deferred to Phase 6) |
| Live trading with real funds | RFC-000 (prohibited until calibration complete) |
| Specific Polymarket API details | RFC-002, Polymarket Integration SDD |

### 2.3 Validation Domain

The first paper trading campaign validates against a single market family:

- **Domain identifier:** `FOOTBALL-WINNER`
- **Market type:** Polymarket binary "Winner (Full Time)" contracts
- **Resolution window:** ~90 minutes per match
- **Rationale:** Binary outcome, short resolution cycle, high data density — maximizes calibration evidence in 30 days

Future domains will adopt the same architecture with domain-specific clock frequencies. The architecture is domain-agnostic by design.

---

## 3. Design Principles

These principles derive from the Portable OS Constitution and are non-negotiable for all Paper Trading implementation.

| Principle | Source | Application |
|---|---|---|
| **Deterministic-First** | Constitution A1 | Every pipeline stage produces identical output for identical input. No randomness, no hidden state, no adaptive behavior in the critical path. |
| **Boundary Discipline** | Constitution A3 | Each clock defines MUST, MUST NOT, and MAY. No responsibility leakage between clocks. |
| **Fail-Fast** | Constitution A4 | Errors surface explicitly. Silent recovery and hidden fallbacks are prohibited. Every failure produces a traceable artifact. |
| **Simplicity Doctrine** | Constitution A5 | No component exists without demonstrable necessity. Four clocks. One scheduler. Zero orchestration frameworks. |
| **Governance Minimalism** | Constitution A6 | No new governance layers. Human authority externalized. Rules frozen before execution. |
| **Validate Uncertainty First** | Constitution A7 | The 30-day experiment exists to validate the risk center (does the pipeline work with real data?) before scaling to multiple domains or autonomous coordination. |
| **Evidence Before Complexity** | Constitution A8 | No implementation advances without verifiable evidence. Every session produces SHA-256 checksummed artifacts. |
| **Integration Hostility** | Constitution B2 | No cloud SDKs. No message queues. No external orchestration. SQLite + cron + Python stdlib. |
| **Human Sovereignty** | RFC-007 | The operator owns capital allocation, market domain selection, frozen rule definition, and override authority. The pipeline executes, never governs. |

---

## 4. Accepted Architectural Decisions

These decisions are frozen. They will not be revisited during implementation.

### AD-1: Event-Centric Architecture

Paper Trading is organized around events (market data observations) rather than sessions. "Session" is an operational grouping mechanism, not a domain concept. The true domain entities are Markets, Events, Decisions, and Reflections.

### AD-2: Four Operational Clocks

The architecture decomposes into four independent clocks: Discovery, Evidence, Decision, and Reflection. Each clock owns exactly one bounded responsibility, executes at its natural frequency, tracks its own progress, and recovers independently from failure.

### AD-3: Unidirectional Dependencies

Dependencies flow strictly in one direction: Discovery → Evidence → Decision → Reflection. No clock depends on a downstream clock. No circular dependencies exist. Coordination is emergent from the data flow, not orchestrated.

### AD-4: Deterministic Market Rotation

Market rotation — replacing expired Condition IDs to preserve evidence continuity — is a deterministic operation. The guard script applies frozen eligibility rules defined by the human operator before Day 0. No AI, no ranking, no optimization, no strategic selection.

### AD-5: Human Governance Externalized

The human operator defines frozen rules before the experiment begins. During the 30 days, the pipeline executes those rules without human intervention for individual sessions. The operator reviews accumulated evidence in batched windows (approximately every 7 days) and may adjust frozen rules if necessary. Every adjustment is version-controlled and timestamped.

See Section 19.1 for detailed authority boundaries.

### AD-6: Hermes Excluded from Critical Path

Hermes and all intelligence systems are excluded from market discovery, market selection, signal generation, trade execution, and evidence continuity. Hermes' role is limited to post-execution reflection augmentation as defined by RFC-005.

### AD-7: Continuous Operation via OS Scheduler

Execution is driven by cron (Linux) at 15-minute intervals. Each cron trigger invokes the guard script followed by the paper trading CLI. No long-running daemon, no coordinator process, no orchestration framework.

### AD-8: Sub-Daily Reconstruction

The session reconstruction mechanism (`_reconstruct_stages`) tracks progress per clock, not per calendar day. This enables sub-daily execution without data loss or redundant processing.

### AD-9: 15-Minute Execution Rhythm

Evidence capture executes every 15 minutes. This frequency was selected to maximize calibration evidence density — 2,880 sessions in 30 days — while remaining at the point where diminishing returns begin for football match coverage.

See OC-1 for the operational schedule specification.

### AD-10: VPS Deployment

Continuous 30-day operation requires a Linux VPS (any provider). Local workstations cannot guarantee the uptime required for unattended 24/7 execution.

---

## 5. Final Operational Architecture

```
                              ┌─────────────────────┐
                              │   HUMAN OPERATOR    │
                              │                     │
                              │ • Defines frozen    │
                              │   eligibility rules │
                              │ • Selects domain    │
                              │ • Reviews evidence  │
                              │   every ~7 days     │
                              │ • Retains override  │
                              │   authority         │
                              └────────┬────────────┘
                                       │ rules, domain
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        VPS — Linux + Python 3.12 + cron              │
│                                                                      │
│  cron every 15 minutes:                                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1. ensure_active_market.py (DISCOVERY GUARD)                  │   │
│  │    ├─ Detect expired markets                                  │   │
│  │    ├─ If expired: GET /markets → filter frozen rules          │   │
│  │    │             → take first valid → update .env             │   │
│  │    └─ Log rotation event                                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 2. trady-ai paper-trade session                               │   │
│  │    --domain FOOTBALL-WINNER --non-interactive                  │   │
│  │                                                                │   │
│  │    PRE_FLIGHT → CAPTURING (60s) → EXECUTING → REFLECTING      │   │
│  │    → VERIFYING → BUNDLING → COMPLETE                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ OUTPUT (per session):                                          │   │
│  │   paper_trading/dia-NNN/                                       │   │
│  │   ├── session_report.json    (day, domain, market_ids,        │   │
│  │   │                           event_count, trade_count,        │   │
│  │   │                           calibration_state, timestamps)   │   │
│  │   ├── contracts.json         (contract violations)             │   │
│  │   └── manifest.json          (SHA-256 checksums)               │   │
│  │                                                                │   │
│  │   data/trady_ai.db                                            │   │
│  │   ├── event_store   (every captured tick)                     │   │
│  │   ├── signals       (every generated signal)                   │   │
│  │   ├── trades        (every executed trade)                     │   │
│  │   └── reflection_reports (every analysis)                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  cron daily at 02:00:                                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ cp data/trady_ai.db data/backups/trady_ai-$(date +%Y%m%d).db │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Operational Clocks

### 6.1 Clock Definitions

| Clock | Responsibility | Frequency | Input | Output | Owner (RFC) |
|---|---|---|---|---|---|
| **Discovery** | Maintain the catalog of observable markets: scan platforms, apply eligibility rules, activate valid markets, detect expirations, retire expired markets | Every 15 min (pre-session guard) | Platform REST APIs, frozen eligibility rules, `.env` | Updated `.env` with active market_ids | RFC-002 (Platform Integration) |
| **Evidence** | Ingest real-time market data: connect to WebSocket, capture price/volume/timestamp events, persist to event_store with deduplication | Every 15 min (60-second capture window) | active market_ids, platform WebSocket | event_store rows | RFC-002 (Platform Integration) |
| **Decision** | Process accumulated events into trading signals and execute trades: run strategy engine over events since last processed seq, generate signals, execute trades, enforce risk constraints | Every session (inline with Evidence) | event_store (since last_processed_seq), strategy (MarkovStrategy), RuntimeConfig | signals rows, trades rows | RFC-001 (Core), RFC-003 (Strategies) |
| **Reflection** | Analyze executed trades for outcomes, drift, signal quality: generate reflection reports, calibration assessments, and bounded parameter proposals | Every session (inline with Decision) | trades rows, signals rows, historical baselines | reflection_reports rows, proposals | RFC-004 (Reflection Systems) |

### 6.2 Clock Independence

Each clock satisfies all criteria for an independent bounded context:

| Criterion | Discovery | Evidence | Decision | Reflection |
|---|---|---|---|---|
| **Owns a distinct responsibility** | ✅ Market catalog management | ✅ Time-series data ingestion | ✅ Signal generation + trade execution | ✅ Outcome analysis + calibration |
| **Has its own lifecycle** | ✅ Discover → Qualify → Activate → Monitor → Retire | ✅ Connect → Capture → Persist → Disconnect | ✅ Load events → Generate signals → Execute trades → Track positions | ✅ Load trades → Analyze outcomes → Detect drift → Generate proposals |
| **Has its own persistence** | ✅ `.env` (active markets) | ✅ `event_store` table | ✅ `signals` + `trades` tables | ✅ `reflection_reports` table |
| **Has explicit contracts** | ✅ Frozen eligibility rules | ✅ Event deduplication, schema validation | ✅ Signal generation contract, risk enforcement | ✅ Proposal-only doctrine, drift thresholds |
| **Fails independently** | ✅ Discovery failure does not block Evidence (uses last known markets) | ✅ Evidence failure does not block Reflection (analyzes existing trades) | ✅ Decision failure preserves events for retry | ✅ Reflection failure preserves execution lineage |
| **Is observable** | ✅ Rotation logs | ✅ Events captured count, WS status | ✅ Signals generated, trades executed | ✅ Reports, proposals, calibration state |

### 6.3 Why Not More Clocks

The architecture was validated for completeness against industry reference models (QuantConnect LEAN) and systematic domain analysis. The following were evaluated and rejected as independent clocks:

- **Calibration Clock:** Calibration is a threshold condition on accumulated Reflection data (30 reports → ready_for_calibration). It is a mode of Reflection at extended frequency, not an independent process.
- **Risk Clock:** Risk enforcement is a constraint applied inline by the Decision Clock. RFC-001 includes risk enforcement as a Core responsibility. In LEAN, RiskManagement runs inline between PortfolioConstruction and Execution.
- **Portfolio Clock:** Position sizing and capital allocation are sub-components of Decision. For the 30-day experiment, position sizing is fixed (`position_size: "10.00"`). Multi-domain portfolio management belongs to Phase 6.
- **Health Clock:** System health monitoring is operational infrastructure (cron exit codes, structlog, disk monitoring), not a domain process.
- **Coordination Clock:** The unidirectional dependency DAG eliminates the need for a coordinator. Each clock reads from upstream, writes for downstream. The data flow IS the coordination.

---

## 7. Bounded Contexts

### 7.1 Context Boundaries

Each bounded context maps to one operational clock.

#### Discovery Context

```
MUST:
  - Scan platform APIs for available markets
  - Apply frozen eligibility rules to filter candidates
  - Activate valid markets by updating active configuration
  - Detect expired markets (via platform API or zero-event signal)
  - Retire expired markets from active configuration
  - Log every activation and retirement with timestamp and rationale

MUST NOT:
  - Capture price events (belongs to Evidence)
  - Generate trading signals (belongs to Decision)
  - Execute trades (belongs to Decision)
  - Analyze trade outcomes (belongs to Reflection)
  - Rank or optimize markets (belongs to Governance)
  - Define eligibility rules (belongs to Governance)

MAY:
  - Maintain a watchlist of pre-qualified candidates
  - Persist market discovery history for audit
  - Expose market_ids to Evidence via environment configuration
```

#### Evidence Context

```
MUST:
  - Connect to platform WebSocket for configured market_ids
  - Capture every price/volume/timestamp event
  - Deduplicate events by (market_id, timestamp, event_type) composite key
  - Persist events to event_store with monotonically increasing sequence numbers
  - Handle WebSocket disconnection with explicit logging
  - Respect the 60-second capture window in non-interactive mode

MUST NOT:
  - Discover or select markets (belongs to Discovery)
  - Generate trading signals (belongs to Decision)
  - Execute trades (belongs to Decision)
  - Analyze event patterns (belongs to Reflection)
  - Modify event data during ingestion

MAY:
  - Perform gap-fill via REST API on reconnection (best-effort, not guaranteed)
  - Track connection health metrics
```

#### Decision Context

```
MUST:
  - Load events from event_store since last_processed_seq
  - Apply deterministic strategy (MarkovStrategy) to generate signals
  - Execute trades based on generated signals
  - Enforce risk constraints (stop_loss_pct, position_size)
  - Persist signals and trades with deterministic UUIDs
  - Track position lifecycle (OPEN → CLOSED)

MUST NOT:
  - Discover or select markets (belongs to Discovery)
  - Capture raw events (belongs to Evidence)
  - Modify strategy parameters autonomously (belongs to Governance)
  - Generate reflection proposals (belongs to Reflection)

MAY:
  - Accept strategy instances via dependency injection
  - Track execution metrics for downstream analysis
```

#### Reflection Context

```
MUST:
  - Load trades and signals from the database
  - Compute outcome summary (win rate, PnL, drawdown)
  - Detect signal quality degradation (accuracy trends)
  - Detect parameter drift (deviation from baseline)
  - Generate bounded parameter proposals (with range, justification)
  - Persist reflection reports with domain and period metadata
  - Evaluate calibration readiness after sufficient data accumulation

MUST NOT:
  - Execute trades (belongs to Decision)
  - Mutate strategy parameters directly (proposals only)
  - Bypass governance approval for parameter adoption
  - Capture raw market events (belongs to Evidence)

MAY:
  - Use intelligence systems (Hermes) for augmentation of analysis quality
  - Operate at multiple time scopes (session, daily, weekly)
```

### 7.2 Governance Context (External)

```
MUST:
  - Define frozen eligibility rules before Day 0
  - Select experimental domain (FOOTBALL-WINNER)
  - Approve or reject parameter proposals from Reflection
  - Retain override authority on all automated decisions
  - Review evidence bundles in batched windows (~7 days)

MUST NOT:
  - Intervene in individual session execution
  - Modify frozen rules without version control
  - Delegate governance authority to any clock

MAY:
  - Adjust frozen rules between review windows
  - Terminate the experiment early with explicit justification
```

---

## 8. Dependency Model

### 8.1 Dependency Graph

```
┌────────────┐     market_ids      ┌────────────┐
│ DISCOVERY  │────────────────────▶│  EVIDENCE  │
│   CLOCK    │                     │   CLOCK    │
└────────────┘                     └─────┬──────┘
       ▲                                 │ events
       │ rules                           ▼
       │                        ┌────────────┐
┌──────┴──────┐                 │  DECISION  │
│ GOVERNANCE  │                 │   CLOCK    │
│  (external) │                 └─────┬──────┘
└─────────────┘                       │ trades
                                      ▼
                             ┌────────────┐
                             │ REFLECTION │
                             │   CLOCK    │
                             └────────────┘
```

### 8.2 Dependency Direction

All dependencies are **strictly unidirectional** and flow left-to-right / top-to-bottom.

| Dependency | Direction | Type | Mechanism |
|---|---|---|---|
| Discovery → Evidence | Forward | Data dependency | Discovery writes `TRADY_AI_ACTIVE_MARKETS` to `.env`. Evidence reads `.env` at process start. |
| Evidence → Decision | Forward | Data dependency | Evidence writes to `event_store`. Decision reads from `event_store` filtered by `seq > last_processed_seq`. |
| Decision → Reflection | Forward | Data dependency | Decision writes to `trades`. Reflection reads from `trades` for analysis. |
| Governance → Discovery | External | Rule dependency | Human defines frozen eligibility rules. Discovery applies them deterministically. |
| Governance → all clocks | External | Authority dependency | Human retains freeze, rollback, and override authority over every clock. |

### 8.3 Anti-Dependencies (Explicitly Prohibited)

| Prohibited Dependency | Rationale |
|---|---|
| Evidence → Discovery | Evidence must not decide which markets to capture. It receives market_ids as input. |
| Decision → Evidence | Decision must not trigger data capture. It processes already-persisted events. |
| Reflection → Decision | Reflection must not influence active trading. It operates on historical data only. |
| Any clock → Governance | Clocks execute rules, never define them. Governance is external and authoritative. |
| Clock A → Clock A (self) | No clock may create recursive dependencies or self-modifying behavior. |

---

## 9. Operational Lifecycles

### 9.1 30-Day Experiment Lifecycle

```
Day -1:  FREEZE
         ├── Operator defines eligibility rules
         ├── Operator configures initial ACTIVE_MARKETS
         ├── Operator deploys to VPS
         ├── Operator installs crontab
         └── Operator verifies guard + session dry-run

Day 0:   PRE-FLIGHT
         └── Single manual session to validate all infrastructure

Days 1-30: CONTINUOUS OPERATION
         ├── cron triggers every 15 minutes
         ├── Guard ensures active markets exist
         ├── Pipeline executes: DISCOVER → EVIDENCE → DECISION → REFLECTION
         ├── Evidence bundles written to paper_trading/dia-NNN/
         └── DB backed up daily at 02:00

Day 30:  CALIBRATION GATE
         ├── Reflection computes calibration readiness
         ├── Operator reviews 30 days of evidence
         └── Decision: ready_for_calibration | continue | abort
```

The `dia-NNN` identifier represents the experiment day, not the session number. All sessions executed during the same UTC calendar day belong to the same `dia-NNN` directory. The first session of a new UTC day creates the next `dia-NNN` directory. For the initial 30-day Paper Trading experiment, `NNN` ranges from `001` to `030`.

### 9.2 Market Lifecycle (per market)

```
CREATED (on platform)
    │
    ▼
DISCOVERED (by Discovery Clock: passes eligibility rules)
    │
    ▼
ACTIVATED (written to .env, Evidence Clock begins capture)
    │
    ▼
MONITORED (Evidence Clock captures events; Discovery Clock checks health)
    │
    ├─── EXPIRED (market closed/resolved on platform)
    │         │
    │         ▼
    │    RETIRED (removed from .env, Evidence Clock stops capture)
    │         │
    │         └──→ DISCOVER replacement (guard script)
    │
    └─── ZERO EVENTS (guard detects inactivity)
              │
              ▼
         RETIRED (same as EXPIRED path)
```

### 9.3 Session Lifecycle (per execution)

```
PRE_FLIGHT
    ├── DRY_RUN_ENFORCED: execution_mode == "dry_run"?
    ├── NO_REAL_FUNDS: zero trades with dry_run=0?
    ├── TEMPORAL_INTEGRITY: no duplicate session today?
    ├── ACTIVE_MARKETS_CONFIGURED: market_ids not empty?
    └── ISOLATION_BOUNDARY: session module imports validated?
         │
    ┌────┴────┐
    │  PASS   │  → CAPTURING
    │  FAIL   │  → ERROR (SessionReport with violations)
    └─────────┘

CAPTURING (60 seconds, non-interactive)
    ├── WebSocket connect for market_ids
    ├── Event capture with deduplication
    └── Evidence guard: event_count > 0?
         │
    ┌────┴────┐
    │  PASS   │  → EXECUTING
    │  FAIL   │  → ERROR (EVIDENCE_COMPLETENESS)
    └─────────┘

EXECUTING
    ├── Load events since last_processed_seq
    ├── Run MarkovStrategy → generate signals
    ├── Execute trades (dry_run=1)
    └── Persist signals + trades
         │
    ┌────┴────┐
    │  PASS   │  → REFLECTING
    │  FAIL   │  → ERROR (events preserved, retryable)
    └─────────┘

REFLECTING
    ├── OutcomeAnalyzer: trade outcomes
    ├── SignalQualityAnalyzer: signal accuracy
    ├── DriftAnalyzer: parameter deviation
    ├── ProposalGenerator: bounded proposals
    └── Persist reflection_report
         │
    ┌────┴────┐
    │  PASS   │  → VERIFYING
    │  FAIL   │  → ERROR (execution preserved, retryable)
    └─────────┘

VERIFYING
    ├── NO_REAL_FUNDS (re-check)
    ├── EVIDENCE_COMPLETENESS: reflection_report exists?
    ├── DETERMINISTIC_REPRODUCIBILITY: replay verification
    └── REFLECTION_ISOLATION: reflection tables only?
         │
    ┌────┴────┐
    │  PASS   │  → BUNDLING
    │  FAIL   │  → ERROR (with violation details)
    └─────────┘

BUNDLING
    ├── Generate session_report.json
    ├── Generate contracts.json
    ├── Compute SHA-256 checksums
    └── Write manifest.json
         │
         ▼
      COMPLETE
```

---

## 10. Architectural Contracts

### AC-1: Deterministic Pipeline Contract

Every stage of the pipeline MUST produce identical output given identical input state. This contract is verified at two levels:

- **Per-session:** `verify_replay()` in VERIFYING stage. A fresh strategy instance re-processes the same events and must produce identical signals and trades.
- **Cross-session:** Any two sessions with the same `market_ids`, same `since_seq`, same strategy parameters, and same event_store state must produce identical `SessionReport` data.

### AC-2: Evidence Integrity Contract

Every session produces a SHA-256 checksummed evidence bundle. The bundle MUST be reproducible from the database state alone. Calling `EvidenceBundler.regenerate_bundle(day, domain)` with the same database state MUST produce bit-identical artifacts.

### AC-3: Clock Isolation Contract

No clock may import or depend on modules belonging to another clock's bounded context. Specifically:

- Evidence MUST NOT import from Decision or Reflection
- Decision MUST NOT import from Reflection
- Discovery MUST NOT import from Evidence, Decision, or Reflection

Cross-clock communication occurs exclusively through the database and configuration files.

### AC-4: Reconstruction Contract

After any interruption, the system MUST be able to reconstruct its operational state from persisted evidence and continue from the first incomplete stage. Reconstruction tracks progress per-clock:

- **Discovery:** last rotation timestamp and current active market_ids
- **Evidence:** `max_seq` in event_store (resume capture from last persisted event)
- **Decision:** `last_processed_seq` (process only new events since that sequence)
- **Reflection:** `last_report_date` (analyze only trades since that date)

Reconstruction MUST NOT use calendar day (`DATE(timestamp) = today`) as the sole granularity. Sequence numbers and timestamps provide sub-daily precision.

---

## 11. Operational Contracts

### OC-1: Execution Rhythm Contract

| Parameter | Value | Justification |
|---|---|---|
| **Scheduler** | cron (POSIX) | Universal on Linux. Explicit, observable, replaceable. |
| **Interval** | 15 minutes | 2,880 sessions/30 days. SE = 1.86%. Captures 7-8 snapshots per football match. Point of diminishing returns for match coverage. |
| **Command** | `trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive` | Single invocation, zero interaction required. |
| **Pre-command** | `python scripts/ensure_active_market.py --domain FOOTBALL-WINNER` | Guard script runs before every session. |
| **Capture window** | 60 seconds | Sufficient to accumulate ticks without excessive WS connection time. |
| **Idempotency** | Guaranteed by per-clock reconstruction | Multiple executions within the same window skip already-completed stages. |

### OC-2: Evidence Continuity Contract

The guard script (`ensure_active_market.py`) MUST execute before every paper trading session.

```
Algorithm:
  1. Read TRADY_AI_ACTIVE_MARKETS from .env
  2. For each Condition ID:
     a. Query platform API: GET /market/{id}
     b. If closed == true OR api returns 404 → mark as EXPIRED
  3. If ALL markets are EXPIRED:
     a. Query platform API: GET /markets
     b. Filter by frozen eligibility rules:
        - tags contains "football" AND "winner"
        - active == true
        - closed == false
     c. If no markets pass eligibility → exit 1 (fail-fast)
     d. Take the FIRST market that passes (no ranking, no optimization)
     e. Write to .env: TRADY_AI_ACTIVE_MARKETS=<new_condition_id>
     f. Log: "ROTATION: 0xOLD → 0xNEW (reason: expired)"
  4. If at least one market is still active → exit 0 (no action)
```

The guard implements evidence continuity, not strategic selection. It answers "is there any valid market?" rather than "which is the best market?"

### OC-3: Governance Boundary Contract

| Decision | Owner | When | Constraint |
|---|---|---|---|
| Define eligibility rules | Human operator | Before Day 0 | Rules must be deterministic (boolean conditions on market metadata) |
| Select experimental domain | Human operator | Before Day 0 | Single domain for first 30-day campaign |
| Modify eligibility rules | Human operator | During review windows (~7 days) | Must be version-controlled (git commit) |
| Override active markets | Human operator | Any time | Direct .env edit takes precedence over guard script |
| Approve parameter proposals | Human operator | After Reflection generates proposals | No automatic parameter adoption |
| Terminate experiment | Human operator | Any time | Requires explicit justification |
| Execute individual sessions | Pipeline (automated) | Every 15 minutes | No human intervention per session |
| Rotate expired markets | Guard script (automated) | Pre-session | Applies frozen rules deterministically |
| Generate trading signals | Decision Clock (automated) | Per session | MarkovStrategy, fixed parameters |

### OC-4: Failure Recovery Contract

| Failure | Detection | Response | Recovery |
|---|---|---|---|
| Guard script fails (no valid markets) | exit code ≠ 0 | Session does not start | Next cron execution retries guard |
| Capture fails (WS disconnect) | Exception in `_do_capture` | Session enters ERROR state | Next session reconnects. Events preserved. |
| Execute fails (engine error) | Exception in `_do_execute` | Session enters ERROR state | Events preserved. Retry with same `since_seq`. |
| Reflect fails (analysis error) | Exception in `_do_reflect` | Session enters ERROR state | Execution preserved. Retry reflection. |
| Duplicate session | TEMPORAL_INTEGRITY violation | PRE_FLIGHT rejects → ERROR | Next scheduled session proceeds normally |
| DB corruption | Backup integrity check | Operator alerted | Restore from daily backup (`data/backups/`) |
| Disk full | cron log monitoring | Sessions fail to write bundles | Operator alerted. Free disk space. Sessions resume. |

### 20.4 Backlog Integration

All operational findings discovered during the 30-day campaign — including bugs, contract violations (CRITICAL and WARNING), unexpected behaviors, failed experiments, operational anomalies, and improvement opportunities — MUST be recorded as `BL-XXX` entries following the Backlog Protocol (`BACKLOG-PROTOCOL.md`).

Findings are triaged during the operator's review windows (approximately every 7 days) and may also be added ad-hoc when the operator detects an anomaly during any VPS session.

Post-campaign, the accumulated Backlog entries inform the design of Phase 6+ architecture, governance policies, and autonomous coordination contracts.

---

## 12. Governance Constraints

### 12.1 Authority Hierarchy

```
Governance (Human Operator)
    │
    ├── Defines frozen rules
    ├── Selects domain
    ├── Approves parameter changes
    ├── Retains override authority
    └── Reviews evidence
         │
         ▼
    ┌─────────────────────────────────────┐
    │         DETERMINISTIC PIPELINE       │
    │                                     │
    │  Discovery → Evidence → Decision    │
    │  → Reflection                       │
    │                                     │
    │  Executes rules. Never defines them. │
    └─────────────────────────────────────┘
```

### 12.2 Prohibited Governance Patterns

| Pattern | Rationale |
|---|---|
| Pipeline defining its own eligibility rules | Rules belong to Governance, not Execution |
| Automatic adoption of Reflection proposals | RFC-004: proposals require governance review |
| Hermes selecting markets or strategies | RFC-005: intelligence assists, does not own operations |
| Unversioned rule changes | RFC-007: all mutations must be attributable and reversible |
| Governance delegation to any clock | RFC-007: human sovereignty is non-delegable |

### 12.3 Override Protocol

The human operator may override any automated decision at any time:

1. Edit `.env` directly to change `TRADY_AI_ACTIVE_MARKETS`
2. Edit `ensure_active_market.py` to change frozen eligibility rules
3. The change takes effect on the NEXT cron execution (new process reads fresh `.env`)
4. Every override MUST be version-controlled (`git commit`) with rationale

---

## 13. Deterministic Constraints

### 13.1 Sources of Determinism

| Component | Deterministic Property | Verification |
|---|---|---|
| `EventCapture` | Same market_ids + same WS connection → same events (deduplication by composite key) | Per-session: event_count is deterministic for a given time window |
| `PolymarketAdapter.market_to_input()` | Same raw API response → same `MarketInput` | Pure function. Unit tested. |
| `MarkovStrategy` | Same event sequence → same signal sequence | `verify_replay()` in VERIFYING stage |
| `ExecutionEngine` | Same inputs + same strategy → same `ExecutionResult` | `verify_replay()` in VERIFYING stage |
| `EvidenceBundler` | Same DB state → same bundle (identical SHA-256) | `regenerate_bundle()` produces identical checksums |
| Guard script | Same eligibility rules + same API state → same market selection | `take the first market that passes rules` — no randomness, no ranking |

### 13.2 Sources of Non-Determinism (Accepted and Contained)

| Source | Why It's Accepted | Containment |
|---|---|---|
| WebSocket event timing | Polymarket emits events at its own rhythm | Each session captures whatever events arrived in its 60-second window. This is the ground truth being measured. |
| Platform API availability | External dependency | Fail-fast: if API is down, session errors explicitly |
| Network latency | Physical constraint | Not relevant at 15-minute intervals |
| Market resolution timing | External event (match ends) | Guard script detects via API, not via timing assumptions |

### 13.3 Forbidden Non-Determinism

| Pattern | Why Forbidden |
|---|---|
| Random market selection | Violates A1. Every decision must be reproducible. |
| LLM-based eligibility decisions | Violates RFC-005. Intelligence is for analysis, not operations. |
| Adaptive capture windows | Violates A1. Capture window is fixed at 60 seconds. |
| Probabilistic signal generation | Violates RFC-001. Strategies must be deterministic. |
| Time-based randomness (seeds, jitter) | Violates A1. Every execution must be reproducible. |

---

## 14. Evidence Architecture

### 14.1 Evidence Types

| Evidence Type | Storage | Produced By | Retention |
|---|---|---|---|
| **Raw market events** | `event_store` table (SQLite) | Evidence Clock | Duration of experiment + archive |
| **Trading signals** | `signals` table (SQLite) | Decision Clock | Duration of experiment + archive |
| **Executed trades** | `trades` table (SQLite) | Decision Clock | Duration of experiment + archive |
| **Reflection reports** | `reflection_reports` table (SQLite) | Reflection Clock | Duration of experiment + archive |
| **Session summaries** | `paper_trading/dia-NNN/session_report.json` | Bundling stage | Permanent |
| **Contract validations** | `paper_trading/dia-NNN/contracts.json` | Bundling stage | Permanent |
| **Integrity proofs** | `paper_trading/dia-NNN/manifest.json` | Bundling stage | Permanent |
| **Rotation logs** | `logs/paper-trading.log` (structlog) | Guard script + pipeline | Duration of experiment |
| **DB backups** | `data/backups/trady_ai-YYYYMMDD.db` | cron (daily) | Rolling 30 days |

### 14.2 Evidence Chain

```
event_store (raw)
    → signals (derived)
        → trades (derived)
            → reflection_reports (derived)
                → session_report.json (export)
                    → manifest.json (integrity seal)
```

Each layer is derivable from the layer below. The manifest provides cryptographic proof that the exported artifacts match the database state at bundle time.

### 14.3 Operator Review Evidence

After a review window (~7 days), the operator can reconstruct the complete operational history:

```
1. Per-session bundles:
   paper_trading/dia-001/session_report.json  → "Day 1: 847 events, 3 trades, calibration=not_ready"
   paper_trading/dia-002/session_report.json  → "Day 2: 1,203 events, 5 trades"
   ...

2. Rotation history:
   grep ROTATION logs/paper-trading.log
   → "2026-07-15 14:00 ROTATION: 0xabc → 0xdef (reason: expired)"

3. Reflection reports:
   sqlite3 data/trady_ai.db "SELECT id, domain, calibration_state FROM reflection_reports"

4. Contract violations:
   paper_trading/dia-NNN/contracts.json → any CRITICAL or WARNING events
```

---

## 15. Discovery Architecture

### 15.1 Discovery Clock Mechanism

The Discovery Clock is implemented as the `ensure_active_market.py` guard script. It runs synchronously before every Evidence capture cycle.

**Execution model:** Pre-session, single invocation, stateless (reads `.env` + platform API, writes `.env`).

**State tracking:** Rotation log entries in structlog output. Current active market_ids in `.env`.

**Reconstruction:** On restart, Discovery reads `.env` for current state. No reconstruction needed beyond what `.env` already provides.

### 15.2 Eligibility Rules (Frozen Before Day 0)

```python
# Example: Football Winner eligibility rules
ELIGIBILITY = {
    "domain": "FOOTBALL-WINNER",
    "platform": "polymarket",
    "required_tags": ["football", "winner"],
    "must_be_active": True,
    "must_not_be_closed": True,
}

# The guard script applies these rules deterministically.
# No ranking. No scoring. No AI. First valid = selected.
```

### 15.3 Rotation Triggers

| Trigger | Detection Method | Response |
|---|---|---|
| Market closed on platform | `GET /market/{id}` → `closed: true` | Mark EXPIRED → find replacement |
| Market returns 404 | `GET /market/{id}` → HTTP 404 | Mark EXPIRED → find replacement |
| All active markets expired | Guard iterates all market_ids, all expired | Full rotation: discover → filter → activate |

---

## 16. Decision Architecture

### 16.1 Decision Clock Mechanism

The Decision Clock executes inline within each Paper Trading session after Evidence capture completes.

**Execution model:** `ExecutionEngine.run_from_store(strategy, since_seq=0)`

**Strategy:** `MarkovStrategy(warmup_ticks=50, threshold_pct=0.001)` — fixed parameters for the 30-day experiment.

**State tracking:** `last_processed_seq` — the maximum event_store sequence number that has been processed into signals.

**Reconstruction:** On restart, Decision loads events where `seq > last_processed_seq` and processes only new events. Already-processed events are never re-processed.

### 16.2 Risk Constraints (Frozen)

| Constraint | Value | Enforcement |
|---|---|---|
| `position_size` | 10.00 USD (fixed) | ExecutionEngine uses this for all trades |
| `stop_loss_pct` | 5% | ExecutionEngine checks before each trade |
| `transaction_cost_pct` | 0.0% | Dry run — no real costs |
| `dry_run` | True | DRY_RUN_ENFORCED contract enforces at PRE_FLIGHT |

---

## 17. Reflection Architecture

### 17.1 Reflection Clock Mechanism

The Reflection Clock executes inline within each Paper Trading session after Decision execution completes.

**Execution model:** `ReflectionEngine.reflect(scope="session", domain=domain, mode="dry_run")`

**Analyzers:**
- `OutcomeAnalyzer`: trade outcomes (win rate, PnL, drawdown)
- `SignalQualityAnalyzer`: signal accuracy trends
- `DriftAnalyzer`: parameter deviation from baseline

**State tracking:** `last_report_date` — the most recent date with a reflection report.

**Reconstruction:** On restart, Reflection loads trades since `last_report_date` and generates a new report spanning that period.

### 17.2 Calibration Gate

After 30 days, the Reflection Engine evaluates calibration readiness:

```
IF reflection_reports >= 30 (one per day)
   AND calibration_state != "ready_for_calibration"
THEN
   _check_calibration_readiness() → "ready_for_calibration"
```

Calibration readiness is a threshold on accumulated evidence, not a separate process.

### 17.3 Hermes Integration Boundary

Hermes MAY augment Reflection analysis quality (RFC-005). Specifically:

- **Permitted:** Enhancing reflection reports with natural language summaries, detecting subtle anomaly patterns, enriching proposal generation with contextual reasoning
- **Prohibited:** Modifying trading signals, altering parameter proposals directly, bypassing governance approval, executing trades

Hermes operates on Reflection OUTPUTS, not on Decision INPUTS. The boundary is explicit: Hermes reads `reflection_reports`, enriches them, and writes augmented summaries. It never touches `event_store`, `signals`, or `trades`.

---

## 18. Infrastructure Model

### 18.1 Runtime Contract

| Requirement | Specification |
|---|---|
| **Operating System** | Linux (any distribution with cron) |
| **Python** | 3.12+ |
| **Package Manager** | `uv` (preferred) or `pip` |
| **Database** | SQLite 3.x (file-based, zero configuration) |
| **Scheduler** | cron (POSIX) |
| **Web Server** | None required |
| **Message Queue** | None required |
| **Container Runtime** | None required (optional: Docker compatible) |

### 18.2 Deployment

```bash
# On any Linux VPS:
git clone <repo>
cp .env.example .env
# Edit .env: set TRADY_AI_ACTIVE_MARKETS, POLYMARKET_* (optional for dry_run)
uv sync
crontab -e
# Add:
# */15 * * * * cd /path/to/trady.ai && python scripts/ensure_active_market.py && .venv/bin/trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive >> logs/paper-trading.log 2>&1
# 0 2 * * * cp data/trady_ai.db data/backups/trady_ai-$(date +\%Y\%m\%d).db
```

### 18.3 Portability

The architecture contains zero vendor lock-in:

| Component | Replaceability |
|---|---|
| **VPS provider** | Any Linux host. Migrate via `git clone` + `scp data/` + `scp .env`. |
| **Scheduler** | cron → systemd timer → any POSIX scheduler. One-line change. |
| **Database** | SQLite is a file. `cp` to migrate. |
| **Platform (Polymarket)** | Adapter pattern isolates platform specifics. New platforms require new adapters implementing the same internal contracts. |
| **Strategy (Markov)** | `StrategyBase` ABC allows pluggable strategies. |
| **Intelligence (Hermes)** | Optional augmentation. Reflection functions without it. |

---

## 19. Human Authority Model

### 19.1 Authority Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                 HUMAN OPERATOR AUTHORITY                 │
│                                                         │
│  BEFORE DAY 0:                                          │
│  • Define frozen eligibility rules                       │
│  • Select experimental domain                            │
│  • Configure initial active markets                      │
│  • Deploy infrastructure                                 │
│                                                         │
│  DURING 30 DAYS (review windows ~7 days):               │
│  • Review accumulated evidence bundles                   │
│  • Adjust eligibility rules if needed (versioned)        │
│  • Override active markets if needed                     │
│  • Approve/reject Reflection proposals                   │
│                                                         │
│  AFTER 30 DAYS:                                         │
│  • Evaluate calibration readiness                        │
│  • Decide: graduate to next phase / extend / abort       │
│  • Define policies for future automated operation        │
│                                                         │
│  AT ANY TIME:                                           │
│  • Terminate experiment with justification               │
│  • Override any automated decision                       │
│  • Direct SSH access to VPS                              │
└─────────────────────────────────────────────────────────┘
```

### 19.2 What the Operator Does NOT Do

- ❌ Manually execute individual sessions (cron handles this)
- ❌ Manually rotate expired markets (guard script handles this)
- ❌ Monitor sessions in real-time (evidence bundles enable batched review)
- ❌ Generate trading signals (Decision Clock handles this)
- ❌ Adjust strategy parameters mid-experiment (parameters are frozen)

---

## 20. Failure Model

### 20.1 Failure Classification

| Severity | Meaning | Examples | Response |
|---|---|---|---|
| **CRITICAL** | Session cannot continue. Violates a frozen contract. | DRY_RUN_ENFORCED violation, real funds detected | Session enters ERROR state. Bundle written with violation details. Operator alerted at next review. |
| **ERROR** | Stage failed but state is preserved for retry. | WebSocket disconnect, API timeout, engine exception | Session enters ERROR state. Next cron execution retries from first incomplete stage (reconstruction). |
| **WARNING** | Non-blocking anomaly detected. | Slight parameter drift, replay verification warning | Logged. Bundle written with WARNING severity. Does not halt session. |

### 20.2 Failure Isolation

| Failure In | Affects | Does NOT Affect |
|---|---|---|
| Guard script (no markets found) | Current session does not start | DB integrity, previous evidence, other clocks |
| Evidence Clock (WS disconnect) | Current session capture stage | DB integrity, previous events, Decision/Reflection on existing data |
| Decision Clock (engine error) | Current session signal generation | event_store integrity, previous trades |
| Reflection Clock (analysis error) | Current session reflection report | trade and signal integrity, previous reports |
| Entire VPS (power loss, reboot) | Session in progress | All persisted data in DB and bundles. Recovery via reconstruction on next boot. |

### 20.3 Recovery Time Objective (RTO)

| Scenario | RTO | Mechanism |
|---|---|---|
| Single session failure | 15 minutes (next cron execution) | `_reconstruct_stages()` in `PaperTradingSession` skips already-completed stages |
| Guard script failure (API down) | Variable (when API recovers) | Each cron execution retries guard |
| VPS reboot | ~2 minutes (boot + cron resume) | cron starts triggering on boot |
| DB corruption | ~10 minutes (restore backup + replay) | Daily backup + reconstruction from last seq |
| Disk full | Operator-dependent | Alert → operator frees space → sessions resume |

---

## 21. Scalability Model

### 21.1 Domain Scalability

The architecture scales from 1 domain to N domains without structural changes:

| Scale | Discovery | Evidence | Decision | Reflection |
|---|---|---|---|---|
| **1 domain (FOOTBALL-WINNER)** | 1 guard script, 1 set of rules | 1 WS connection, ~5-10 markets | 1 strategy, 1 engine | 1 set of analyzers |
| **N domains** | N guard scripts OR 1 guard with N rule sets | N WS connections (or multiplexed) | N strategies (1 per domain) | N analyzer configs (1 per domain) |

Domain isolation (RFC-006) is preserved: each domain has independent event sequences, independent signals, independent trades, and independent reflection baselines.

### 21.2 Data Volume Scalability

| Metric | 1 domain, 30 days | 5 domains, 30 days | Bottleneck |
|---|---|---|---|
| **Sessions** | 2,880 | 14,400 | cron capacity (96/day is trivial) |
| **Events** | ~500K-5M | ~2.5M-25M | SQLite handles 10M+ rows comfortably |
| **DB size** | ~50-500 MB | ~250 MB-2.5 GB | Single SQLite file. Backup size grows linearly. |
| **WS connections** | 96/day | 480/day | Polymarket rate limits (TBD). Mitigation: connection pooling. |
| **CPU** | ~2.8 hrs runtime/30d | ~14 hrs runtime/30d | Any VPS handles this |

### 21.3 Platform Scalability

Adding a new platform (e.g., crypto exchange) requires:
1. New adapter implementing `PolymarketAdapter`-equivalent interface
2. New guard script variant with platform-specific eligibility rules
3. New domain identifier

The clock architecture, dependency model, evidence architecture, and governance model remain unchanged.

---

## 22. RFC Alignment

### 22.1 Alignment Matrix

| RFC | Doctrine | Paper Trading Alignment |
|---|---|---|
| **RFC-000** | Security + Operational Safety | Dry run enforced, no real funds, fail-fast, secrets isolation, runtime hardening (no daemons, no hidden services) |
| **RFC-001** | Deterministic Core | MarkovStrategy is deterministic. ExecutionEngine produces reproducible outputs. verify_replay() validates. |
| **RFC-002** | Platform Integration | PolymarketAdapter isolates external API. Adapters translate structure, never own meaning. |
| **RFC-003** | Strategy Infrastructure | MarkovStrategy is modular, replaceable, statistically traceable. Fixed parameters for 30-day baseline. |
| **RFC-004** | Reflection Systems | Reflection analyzes post-execution. Generates bounded proposals. Never controls execution. |
| **RFC-005** | Intelligence Integration | Hermes excluded from critical path. Used only for reflection augmentation. Model-agnostic. |
| **RFC-006** | Multi-Domain Execution | FOOTBALL-WINNER is first domain. Architecture supports isolation of future domains. |
| **RFC-007** | Governance Hardening | Human retains capital allocation, rule definition, and override authority. Pipeline executes, never governs. |
| **RFC-008** | Autonomous Coordination | Deferred to Phase 8. Current cron scheduling is OS infrastructure, not autonomous coordination. |
| **RFC-009** | Universal Financial Infrastructure | Architecture is platform-agnostic, model-agnostic, domain-agnostic. Provider-independent. |

### 22.2 No RFC Violations

The Paper Trading architecture has been audited against all nine RFCs. Zero violations were found. Every architectural decision traces back to an explicit RFC doctrine.

---

## 23. Deferred Decisions

These decisions are explicitly deferred to future phases. They are NOT required for the 30-day paper trading experiment.

| Decision | Deferred To | Rationale |
|---|---|---|
| Automatic discovery without guard script | Phase 8 (Autonomous Coordination) | Requires bounded autonomy contracts not yet implemented |
| Multi-domain simultaneous operation | Phase 6 (Multi-Domain Execution) | Single domain sufficient for calibration |
| Dynamic strategy parameter adjustment | Phase 8 | Requires governance-approved adaptation policies |
| Hermes as operational operator | Phase 8 | Requires full RFC-008 implementation |
| Real-fund trading | Phase 9+ | Requires calibration readiness + governance approval |
| Cross-platform market discovery | Phase 9 (Universal Infrastructure) | Polymarket is the only integrated platform |
| Portfolio-level capital allocation | Phase 6 | Position size is fixed for the experiment |
| Continuous 24/7 market data capture (uninterrupted event ingestion without gaps between 60-second capture windows) | Phase 6 | The system already operates continuously (96 sessions/day at 15-minute intervals). The deferred capability is eliminating the 14-minute gaps between 60-second capture windows — i.e., ingesting market data as a continuous 24/7 stream. Current discrete-window capture is sufficient for calibration. |

---

## 24. Explicitly Rejected Alternatives

These alternatives were evaluated and explicitly rejected. They are documented to prevent re-litigation.

### RA-1: Session-Centric Architecture
**Rejected because:** Session is an operational artifact, not a domain concept. Couples Evidence, Decision, and Reflection in lockstep. Prevents independent clock frequencies. Causes reconstruction bottleneck at sub-daily granularity.

### RA-2: Hermes in Operational Critical Path
**Rejected because:** Violates RFC-005 (intelligence assists, does not own operations). Market discovery is deterministic (API query + filter). Candidate evaluation is deterministic (mathematical thresholds). AI adds latency, cost, and non-determinism to a pipeline that doesn't need it.

### RA-3: "Temporary Operational Governance Layer"
**Rejected because:** Violates Constitution A6 (Governance Minimalism). Duplicates RFC-007 governance authority. "Temporary" layers create dependency and removal friction. The existing governance model (human + frozen rules) is sufficient.

### RA-4: Market Rotation as Strategic Selection
**Rejected because:** Conflates two distinct responsibilities. Strategic selection (choosing the "best" market) is governance. Evidence continuity (ensuring any valid market exists) is operational infrastructure. The guard script implements the latter.

### RA-5: Coordinator Daemon / Long-Running Process
**Rejected because:** Violates RFC-000 §Runtime Hardening ("uncontrolled daemons" rejected). Single point of failure. cron provides process isolation — each execution is a fresh Python process. A crashed session doesn't affect the next one.

### RA-6: Event-Driven Scheduling (Match Fixtures)
**Rejected because:** Introduces external dependency on football fixture data. Violates Constitution B2 (Integration Hostility). Markets are active 24/7 — fixed-interval scheduling captures pre-match, in-match, and post-match data without fixture knowledge.

### RA-7: 6-Hour or 3-Hour Execution Rhythm
**Rejected because:** 15 minutes provides 2× to 4× more calibration data (2,880 vs 720-1,440 sessions). Football match coverage improves from 1-2 snapshots to 7-8 snapshots per match. The operational cost difference is negligible on a VPS.

### RA-8: Direct .env Mutation Within Session Process
**Rejected because:** Settings is frozen (`frozen=True`) with `@lru_cache`. Modifying `.env` mid-process does not update Settings. The guard script runs as a separate process before the session, ensuring fresh Settings for each execution.

### RA-9: Calendar-Day Reconstruction Granularity
**Rejected because:** `DATE(timestamp) = today` limits meaningful sessions to once per day. Sub-daily execution requires per-sequence reconstruction tracking progress by `max_seq`, not calendar date.

---

## 25. Implementation Constraints

### 25.1 Must Preserve

| Constraint | Scope |
|---|---|
| All 9 RFCs | Architecture-wide |
| All 7 Constitution Principles (A1-A7) | Architecture-wide |
| All 4 Architectural Contracts (AC-1 to AC-4) | Implementation |
| All 4 Operational Contracts (OC-1 to OC-4) | Operations |
| Dry-run enforcement (`dry_run=True`) | All sessions |
| Deterministic replayability | All sessions |
| Evidence bundling (SHA-256) | All sessions |
| Backlog protocol for operational findings | All bugs, contract violations, anomalies, and improvement opportunities |
| Human sovereignty | Governance boundary |

### 25.2 Must Not Introduce

| Prohibited | Rationale |
|---|---|
| New governance layers | A6: Governance Minimalism |
| AI in market selection | RFC-005: Proposal-Only Doctrine |
| Orchestration frameworks | RFC-000: Runtime Hardening |
| Cloud vendor SDKs | B2: Integration Hostility |
| Probabilistic decision-making | A1: Deterministic-First |
| Hidden services or daemons | RFC-000: Operational Transparency |
| New bounded contexts beyond 4 clocks | Completeness validated |

### 25.3 Implementation Scope for Day 0 Readiness

These are the implementation items required before the 30-day experiment can begin:

1. **`ensure_active_market.py` guard script** — deterministic market rotation
2. **Refined `_reconstruct_stages`** — per-sequence tracking instead of per-calendar-day
3. **`SessionReport.market_ids` field** — capture which markets were used in each session
4. **`--duration` flag on `capture` CLI** (optional) — or use session's built-in 60s timeout
5. **crontab deployment** — 15-minute interval configuration
6. **Daily DB backup** — one-line cron job
7. **Initial `TRADY_AI_ACTIVE_MARKETS` configuration** — 5-10 Condition IDs for first week
8. **Frozen eligibility rules** — documented and version-controlled

---

## 26. Freeze Checklist

| # | Item | Status |
|---|---|---|
| 1 | Four operational clocks accepted as complete architecture | ✅ FROZEN |
| 2 | Unidirectional dependency model (DAG) | ✅ FROZEN |
| 3 | 15-minute execution rhythm | ✅ FROZEN |
| 4 | Guard script for deterministic evidence continuity | ✅ FROZEN |
| 5 | Human governance externalized | ✅ FROZEN |
| 6 | Hermes excluded from critical path | ✅ FROZEN |
| 7 | VPS + cron deployment model | ✅ FROZEN |
| 8 | FOOTBALL-WINNER as first validation domain | ✅ FROZEN |
| 9 | Per-clock reconstruction (not per-calendar-day) | ✅ FROZEN |
| 10 | 60-second capture window in non-interactive mode | ✅ FROZEN |
| 11 | SHA-256 evidence bundling per session | ✅ FROZEN |
| 12 | Daily DB backup | ✅ FROZEN |
| 13 | All 4 Architectural Contracts accepted | ✅ FROZEN |
| 14 | All 4 Operational Contracts accepted | ✅ FROZEN |
| 15 | All 9 Rejected Alternatives documented | ✅ FROZEN |
| 16 | No RFC violations identified | ✅ FROZEN |
| 17 | Scalability to N domains validated | ✅ FROZEN |
| 18 | Failure model with RTO defined | ✅ FROZEN |
| 19 | Implementation constraints documented | ✅ FROZEN |
| 20 | Deferred decisions catalogued | ✅ FROZEN |

---

## 27. Final Freeze Declaration

```
═══════════════════════════════════════════════════════════════
                                                              
     PAPER TRADING ARCHITECTURE — PERMANENT FREEZE            
                                                              
     This architecture is FROZEN effective immediately.       
                                                              
      Status:   FROZEN                                         
      Version:  2.0                                            
      Date:     Prior to Day 0 of 30-day campaign              
      Last amended: 2026-07-27 (v1.0→v2.0: multi-domain        
                    support, documented deviations,             
                    Binance platform integration)
                                                              
     The Paper Trading operational architecture is            
     considered conceptually complete and internally          
     consistent.                                              
                                                              
     All 27 sections of this contract have been               
     validated against:                                       
       • PORTABLE-OS-CONSTITUTION (all 8 mandatory            
         principles + all 6 recommended principles)           
       • RFC-000 through RFC-009 (zero violations)            
       • TRADY-AI-MASTER-ROADMAP-001 (Phase 5 scope           
         respected, no phase leakage)                         
       • Industry reference architecture (QuantConnect        
         LEAN framework validation)                           
                                                              
     NO architectural changes are permitted without:          
       1. Explicit governance review                          
       2. Amendment to this contract                          
       3. Version increment                                   
       4. Impact assessment against all frozen RFCs           
                                                              
     Implementation may proceed under this contract.          
                                                              
     Future SDD cycles, reviews, audits, and RFC              
     evolutions MUST treat this document as the               
     authoritative Paper Trading Source of Truth.             
                                                              
═══════════════════════════════════════════════════════════════
```

---

## 28. Amendment Log

| Version | Date | Sections Changed | Description |
|---------|------|-----------------|-------------|
| **1.0 → 2.0** | 2026-07-27 | §27 (Freeze), +§28 (Amendment Log), +§29 (Documented Deviations), +§30 (Multi-Domain Architecture) | Formalize BL-027 (OC-2 discovery deviation), BL-028 (multi-domain support), Binance platform integration. Three SDD cycles validated (calibration-framework, guard-script-domain-agnostic, binance-adapter). |

## 29. Documented Deviations & Errata

### D-001: OC-2 Market Discovery Mechanism (BL-027)

**Original contract (OC-2, §2):** Discovery via single `clob.polymarket.com/markets` endpoint with tag filter `["football", "winner"]`.

**Operational reality (2026-07-22):** `clob.polymarket.com/markets` returns `tags=["All"]` for all markets — tag-based filtering is non-functional. Sports markets are only reachable via `polymarket.com/sports/{league}/games` (HTML scraping) → slug extraction → `gamma-api/events?slug={slug}` → condition ID extraction → CLOB verification.

**Impact:** 3-endpoint flow replaces single-endpoint flow. No functional impact on eligibility rules (regex on question field remains deterministic). Documented in `scripts/ensure_active_market.py` docstring, `paper_trading/SESSION-2026-07-22.md`, and `paper_trading/MARKET-DISCOVERY-FIX.md`.

**Status:** ACCEPTED. Guard script validated with 50 tests (2026-07-22). This deviation is a platform limitation, not an architectural choice.

### D-002: Multi-Platform Architecture (BL-028)

**Original contract (v1.0):** Single platform (Polymarket), single domain (FOOTBALL-WINNER).

**Operational reality (2026-07-27):** System supports three domains across two platforms:
- FOOTBALL-WINNER → Polymarket (league-based HTML scraping)
- CRYPTO-BINARY → Polymarket (tag-based gamma API)
- BINANCE-SPOT → Binance (static symbol configuration, no discovery)

**Impact:** Guard script is domain-agnostic (refactored 2026-07-27, SDD cycle). Adapter layer supports multiple platforms via identical contract (`subscribe_websocket` + `market_to_input`). Core engine is unchanged. Calibration framework is domain-agnostic.

**Status:** ACCEPTED. See §30 for multi-domain architecture specification.

## 30. Multi-Domain & Multi-Platform Architecture (v2.0)

### 30.1 Supported Domains

| Domain | Platform | Discovery Strategy | Active Markets Config |
|--------|----------|-------------------|----------------------|
| `FOOTBALL-WINNER` | Polymarket | League-based HTML scraping | `TRADY_AI_FOOTBALL_LEAGUES`, `TRADY_AI_QUESTION_PATTERN` (legacy) |
| `CRYPTO-BINARY` | Polymarket | Tag-based gamma API (`/events?tag_slug=`) | `TRADY_AI_DISCOVERY_TAG_SLUG`, `TRADY_AI_QUESTION_PATTERN` |
| `BINANCE-SPOT` | Binance | Static (no discovery) | `TRADY_AI_ACTIVE_SYMBOLS` |

### 30.2 Platform Adapter Contract

All platform adapters MUST implement:
```python
class Adapter:
    def subscribe_websocket(self, ids: list[str]) -> Generator[dict, None, None]: ...
    @staticmethod
    def market_to_input(raw: dict) -> MarketInput: ...
```

Adapters translate platform-specific data → domain-agnostic `MarketInput`. The core engine, calibration framework, and execution pipeline are platform-independent.

### 30.3 Domain Configuration

Domain selection is via `TRADY_AI_DOMAIN` env var. Valid values: `FOOTBALL-WINNER`, `CRYPTO-BINARY`, `BINANCE-SPOT`. Unknown values cause the guard script to exit with error listing valid domains.

### 30.4 Platform-Specific Configuration

| Platform | Required Env Vars |
|----------|------------------|
| Polymarket | `TRADY_AI_POLYMARKET_REST_URL`, `TRADY_AI_POLYMARKET_WS_URL` |
| Binance | `BINANCE_WS_URL`, `BINANCE_REST_URL`, `TRADY_AI_ACTIVE_SYMBOLS` |

---

**End of Paper Trading Architecture Contract v2.0**
