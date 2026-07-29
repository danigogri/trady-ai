# Reflection Systems Specification

## Purpose

Bounded post-execution evaluation that transforms deterministic execution history into reproducible evidence for Governance. 100% deterministic — no LLM, no random seeds.

**Deterministic boundary**: All analyzers, drift detection, and proposal generation are deterministic. Scheduling triggers and Governance approval/rejection are external.

---

## Module 1: Reflection Data Model

### Requirement: Reflection Report Persistence

The system MUST persist reflection reports with time-bounded scope metadata. The `reflection_reports` table MUST contain: `id` (INTEGER PK), `scope` (TEXT: session|daily|weekly), `domain` (TEXT), `mode` (TEXT: dry_run), `period_start` (TEXT ISO-8601), `period_end` (TEXT ISO-8601), `report_data` (TEXT JSON), `created_at` (TEXT ISO-8601). The `report_data` JSON MAY include an optional `evidence_report` field when a CalibrationAnalyzer is configured.

#### Scenario: Persist a session report

- GIVEN a completed analysis for domain "PM-5M" covering ticks 100-200
- WHEN the ReflectionEngine calls `persist_report()`
- THEN a row is inserted into `reflection_reports` with scope="session", domain="PM-5M", report_data containing outcome_summary, signal_quality, drift_alerts, proposals
- AND created_at is set to current UTC timestamp

#### Scenario: Query reports by time range

- GIVEN 5 reflection reports persisted across 3 days
- WHEN querying with period_start >= "2026-07-10" AND period_end <= "2026-07-12"
- THEN only reports within that range are returned, ordered by created_at DESC

### Requirement: Drift Event Persistence

The system MUST persist drift events when threshold violations are detected. The `drift_events` table MUST contain: `id` (INTEGER PK), `strategy_id` (TEXT), `domain` (TEXT), `metric` (TEXT), `previous_value` (REAL), `current_value` (REAL), `threshold` (REAL), `deviation_pct` (REAL), `detected_at` (TEXT ISO-8601), `acknowledged` (INTEGER DEFAULT 0).

#### Scenario: Persist drift event on threshold breach

- GIVEN a transition probability deviation of 18% (threshold: 15%)
- WHEN DriftAnalyzer detects the breach
- THEN a row is inserted into `drift_events` with deviation_pct=18.0, acknowledged=0

### Requirement: Time-Bounded Query Helpers

The system MUST provide time-bounded query functions in `core/persistence.py` for trades, signals, and strategy_snapshots. All queries MUST use `ORDER BY` for determinism. An index on `event_store(timestamp)` and `trades(timestamp)` MUST be created.

#### Scenario: Query trades in time range

- GIVEN 1000 trades across 7 days
- WHEN `query_trades_by_time_range(db, start, end)` is called
- THEN only trades with timestamp in [start, end] are returned, ordered by timestamp ASC

---

## Module 2: Reflection Analyzers

### Requirement: OutcomeAnalyzer

The system MUST compute from the `trades` and `positions` tables within a time range: `win_rate` (wins/closed), `total_pnl` (sum of closed position PnL), `avg_pnl_per_trade` (total_pnl/closed_count), `max_drawdown` (peak-to-trough). ALL queries MUST use ORDER BY timestamp.

#### Scenario: Compute outcomes for profitable session

- GIVEN 10 closed positions: 7 profitable, 3 losing, total PnL = 150.0
- WHEN OutcomeAnalyzer.analyze(start, end, domain) is called
- THEN result contains win_rate=0.7, total_pnl=150.0, avg_pnl_per_trade=15.0, max_drawdown computed from chronological PnL sequence

#### Scenario: Empty time range

- GIVEN no trades in the specified period
- WHEN OutcomeAnalyzer.analyze() is called
- THEN result contains win_rate=0.0, total_pnl=0.0, avg_pnl_per_trade=0.0, max_drawdown=0.0

### Requirement: SignalQualityAnalyzer

The system MUST compute: `signal_accuracy` (signals that resulted in profitable trades / total signals with trades), `confidence_calibration` (average predicted confidence vs actual win rate in bins). Queries MUST be deterministic.

#### Scenario: Calibrate confidence

- GIVEN 20 signals: 10 with confidence > 0.7 (8 profitable), 10 with confidence <= 0.7 (3 profitable)
- WHEN SignalQualityAnalyzer.analyze() is called
- THEN signal_accuracy = 11/20 = 0.55, confidence_calibration shows high-confidence bin at 80% actual vs low-confidence at 30%

### Requirement: DriftAnalyzer

The system MUST compare two strategy_snapshots for the same (strategy_name, domain). For each cell in transition_counts, compute probability deviation. Flag when ANY deviation exceeds threshold (default: 15%).

#### Scenario: Detect drift in transition matrix

- GIVEN snapshot A: transition_prob(UP→UP) = 0.60, snapshot B: transition_prob(UP→UP) = 0.42
- WHEN DriftAnalyzer.analyze(strategy_id, snapshot_a_tick, snapshot_b_tick) is called
- THEN drift_events row created with metric="transition_UP_UP", deviation_pct=30.0, threshold=15.0

#### Scenario: No drift detected

- GIVEN two snapshots with all probability deviations < 15%
- WHEN DriftAnalyzer.analyze() is called
- THEN no drift_events row is created, result contains drift_detected=false

### Requirement: CalibrationAnalyzer

The system SHALL add `CalibrationAnalyzer` as an injectable analyzer in the
`ReflectionEngine` pipeline. It SHALL consume transition counts + state sequence and
produce a deterministic `EvidenceReport`.

#### Scenario: Analyzer runs in deterministic pipeline order

- GIVEN ReflectionEngine with CalibrationAnalyzer injected after DriftAnalyzer
- WHEN `reflect()` is called
- THEN CalibrationAnalyzer runs in its pipeline position, before report assembly

### Requirement: AIC Computation

`CalibrationAnalyzer.aic(transition_counts, state_sequence) → float` SHALL compute:

$$AIC = -2\ln(L) + 2k \quad\text{where } k = |S|(|S|-1)$$

where $L$ is the Markov chain likelihood: $\prod_{i,j} p_{ij}^{n_{ij}}$ using MLE
$\hat{p}_{ij} = n_{ij}/\sum_j n_{ij}$. AIC MUST be deterministic — same inputs produce
identical float.

#### Scenario: More states penalized

- GIVEN same dataset, |S|=3 AIC=120.5 vs |S|=5
- WHEN both computed
- THEN |S|=5 AIC > |S|=3 AIC unless likelihood improvement justifies the extra params

### Requirement: BIC Computation

`CalibrationAnalyzer.bic(transition_counts, state_sequence, n) → float` SHALL compute:

$$BIC = -2\ln(L) + k\ln(n) \quad\text{where } n = \text{total observations}$$

#### Scenario: BIC stronger penalty than AIC

- GIVEN n=1000 observations, |S|=3 (k=6)
- WHEN AIC and BIC both computed
- THEN BIC penalty = 6·ln(1000) ≈ 41.4 vs AIC penalty = 12

### Requirement: Markov χ² Test

`CalibrationAnalyzer.markov_order_test(state_sequence, |S|, α=0.05) → dict` SHALL
implement the Billingsley χ² test for first-order Markov property:

$$ \chi^2 = \sum_{i,j} \frac{(n_{ij} - e_{ij})^2}{e_{ij}} \quad\text{df}=|S|(|S|-1) $$

Returns: `{statistic, p_value, df, reject_null, significance_level}`.

#### Scenario: Strong Markov signal

- GIVEN a state sequence with clear first-order transitions
- WHEN markov_order_test(α=0.05) called
- THEN reject_null=True, p_value < 0.001

### Requirement: State Persistence and Entropy

The analyzer SHALL compute per-state:
- **Mean residence time**: `1/(1 - p_{ii})` ticks (expected, per diagonal)
- **Conditional entropy**: $H(X_{n+1}|X_n) = -\sum_i \pi_i \sum_j p_{ij}\log_2 p_{ij}$ where $\pi$ is the stationary distribution

#### Scenario: Entropy zero for deterministic chain

- GIVEN a chain where each state transitions deterministically to one next state
- WHEN conditional_entropy() computed
- THEN H = 0.0

### Requirement: EvidenceReport

`EvidenceReport` dataclass SHALL contain: `aic`, `bic`, `markov_test`, `state_persistence`
(dict), `conditional_entropy`, `transition_counts`, `state_sequence_length`,
`computed_at`. All fields are deterministic — same inputs → identical values.

#### Scenario: Serialize to JSON deterministically

- GIVEN the same transition matrix and sequence processed twice
- WHEN `json.dumps(report)` called on both
- THEN byte-identical output

---

## Module 2a: Snapshot Persistence Contracts

### REQ-MC-006: ReflectionEngine Consumes Transition Matrix

`ReflectionEngine` SHALL receive strategy transition matrix data via `ExecutionResult` for snapshot persistence. The engine MUST NOT query `strategy_snapshots` to reconstruct matrix — it consumes what Execution produces.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Engine receives result | ExecutionResult with transition_counts, state_counts, domain="BINANCE-SPOT" | `engine.persist_snapshot(result)` | snapshot persisted with correct domain and strategy metadata |
| Missing matrix | ExecutionResult without transition_counts | `persist_snapshot()` | raises `ValueError("transition_counts required for snapshot")` |

### REQ-MC-007: Snapshot Persistence Frequency and Idempotency

Snapshot SHALL be persisted once per session at the REFLECTING stage. If a snapshot already exists for the same `(strategy_name, domain, tick_number)`, the new write SHALL replace it (idempotent via `INSERT OR REPLACE`). Frequency: exactly 1 snapshot per session per domain.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| First snapshot | No existing row for tick=150 | `persist_snapshot()` | 1 new row in `strategy_snapshots` |
| Duplicate tick | Row exists for strategy/domain/tick=150 | `persist_snapshot()` | existing row REPLACED; no duplicate |
| No duplicate write | Same session, same tick | called twice | second call replaces first; count=1 |

---

## Module 3: Bounded Proposal Generator

### Requirement: Parameter Range Enforcement

The system MUST define bounded ranges for MarkovPersistenceEngine parameters: `warmup_ticks` [10, 200], `threshold_pct` [0.0001, 0.01]. Proposals MUST NOT propose values outside these ranges. Proposals MUST NOT propose strategy swaps or asset changes.

#### Scenario: Generate valid proposal

- GIVEN current warmup_ticks=50, analyzer shows win_rate improved with warmup_ticks=75
- WHEN ProposalGenerator.generate() is called
- THEN proposal created with parameter_name="warmup_ticks", current_value=50, proposed_value=75, range_min=10, range_max=200, status="draft"

#### Scenario: Reject out-of-range proposal

- GIVEN a proposed value of warmup_ticks=500 (exceeds max 200)
- WHEN ProposalGenerator.generate() is called
- THEN the value is clamped to range_max=200, OR no proposal is generated for that parameter

### Requirement: Proposal Schema and Lifecycle

The `proposals` table MUST contain: `id` (INTEGER PK), `strategy_id` (TEXT), `parameter_name` (TEXT), `current_value` (REAL), `proposed_value` (REAL), `range_min` (REAL), `range_max` (REAL), `justification` (TEXT), `status` (TEXT: draft|submitted), `created_at` (TEXT). Lifecycle: draft → submitted. States approved/rejected/deployed are managed by Governance (external).

#### Scenario: Proposal lifecycle

- GIVEN a proposal in status="draft"
- WHEN submit_proposal(proposal_id) is called
- THEN status changes to "submitted"
- AND no further state transitions occur within Reflection boundary

---

## Module 4: Trigger Interface

### Requirement: reflect() Entry Point

The system MUST expose `reflect(scope: Literal["session", "daily", "weekly"], domain: str, mode: Literal["dry_run"]) → ReflectionReport`. The function MUST be deterministic: same inputs produce same outputs. The function MUST NOT mutate production state (only writes to reflection_reports, drift_events, proposals).

#### Scenario: Session reflection

- GIVEN scope="session", domain="PM-5M", mode="dry_run", 50 trades in current session
- WHEN reflect() is called
- THEN ReflectionReport returned with outcome_summary, signal_quality, drift_alerts, proposals, period metadata
- AND report persisted to reflection_reports table

#### Scenario: Weekly reflection with drift

- GIVEN scope="weekly", domain="PM-5M", strategy transition_counts drifted 20%
- WHEN reflect() is called
- THEN ReflectionReport contains drift_alerts with the flagged metric
- AND drift_event persisted to drift_events table
- AND bounded proposal generated IF current_params are out of BOUNDED_PARAMETERS range (clamping)

Note: Deterministic mapping from drift events to parameter proposals is deferred
to Fase 5 (Intelligence). Phase 4 ProposalGenerator handles only range-clamping
proposals. Intelligence (Fase 5) will discover candidate mapping rules from
operational evidence; Governance (Fase 7) approves them as deterministic Proposal Rules.

### Requirement: ReflectionEngine Orchestration (MODIFIED)

The system MUST provide a `ReflectionEngine` class that orchestrates: data scoping (time-bounded queries) → analyzer pipeline (outcome, signal quality, drift, calibration) → **persist_snapshot** → report assembly → persistence. The engine MUST accept a `sqlite_utils.Database`, domain, and optional `calibration_analyzer: CalibrationAnalyzer` as constructor parameters. The engine MUST accept `ExecutionResult` as optional parameter to `reflect()`.

(Previously: no calibration analyzer in the pipeline; no snapshot persistence in ReflectionEngine pipeline.)

#### Scenario: Engine orchestration pipeline

- GIVEN a ReflectionEngine initialized with db and domain="PM-5M"
- WHEN reflect(scope="session", domain="PM-5M", execution_result=result) is called
- THEN analyzers run sequentially in deterministic order
- AND `persist_snapshot(result)` runs after analyzers complete, before report assembly
- AND report is assembled from analyzer outputs (including evidence_report if calibration analyzer configured)
- AND report is persisted before returning

#### Scenario: Engine runs with calibration analyzer

- GIVEN ReflectionEngine with CalibrationAnalyzer injected
- WHEN reflect(scope="weekly", domain="PM-5M") called
- THEN ReflectionReport contains evidence_report field with AIC, BIC, entropy, χ²

#### Scenario: No execution_result skips snapshot

- GIVEN `reflect()` called without `execution_result`
- WHEN no snapshot data available
- THEN snapshot step skipped silently, report assembled normally

---

## Module 5: Paper Trading Operational Contract

### Requirement: Calibration Gate

The system MUST operate with synthetic default thresholds (drift: 15%, parameter ranges as defined) in `uncalibrated` state. After 30 days of accumulated dry_run data, the system SHOULD support a `calibrated` state with reviewed thresholds. Calibration state MUST be queryable.

#### Scenario: Operate in uncalibrated state

- GIVEN calibration_state = "uncalibrated"
- WHEN reflection analysis runs
- THEN synthetic defaults are used (drift threshold = 15%, ranges per Module 3)

### Requirement: Scale Invariance

The system MUST operate identically with 10 rows or 10M rows. All queries MUST be time-bounded and indexed. No full-table scans permitted in analyzer queries.

#### Scenario: Performance with large dataset

- GIVEN event_store with 1M rows, trades with 100K rows
- WHEN reflect() is called for a 1-hour session window
- THEN query execution time is bounded by index scan on timestamp, not full table scan

---

## Data Contracts

| Schema | Key Fields |
|--------|-----------|
| reflection_reports | id, scope, domain, mode, period_start, period_end, report_data (JSON), created_at |
| drift_events | id, strategy_id, domain, metric, previous_value, current_value, threshold, deviation_pct, detected_at, acknowledged |
| proposals | id, strategy_id, parameter_name, current_value, proposed_value, range_min, range_max, justification, status, created_at |
| ReflectionReport | outcome_summary, signal_quality, drift_alerts, proposals, anomalies, period_metadata, evidence_report (optional) |
