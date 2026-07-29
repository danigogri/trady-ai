# Governance Specification

**Domain**: governance (calibration adoption) | **Type**: New | **RFC**: RFC-004 §Governance Boundary
**Research**: CALIBRATION-FRAMEWORK-2026-07-23.md (§Governance)

## Purpose

Define the human-in-the-loop boundary for state-space adoption. Evidence is generated
deterministically; adoption is a governed human decision with immutable provenance.

**Intelligence boundary**: Evidence generation is deterministic. The `calibrate adopt`
decision is human — system SHALL NOT auto-adopt state spaces.

---

## Requirements

### R1: Evidence Review — CLI

`trady-ai calibrate review --domain PM-5M [--strategy directional]` SHALL display:

| Metric | Source |
|--------|--------|
| AIC, BIC | `CalibrationAnalyzer.aic()/bic()` |
| Markov χ² (p-value) | `CalibrationAnalyzer.markov_order_test()` |
| Per-state mean residence time | `CalibrationAnalyzer.state_persistence` |
| Conditional entropy | `CalibrationAnalyzer.conditional_entropy` |

Output MUST be plain text. No interactive prompts. Exit 0 on success.

#### Scenario: Review displays evidence for current state-space

- GIVEN 30 days of paper-trading data for domain PM-5M
- WHEN `calibrate review --domain PM-5M` is run
- THEN AIC, BIC, χ² p-value, entropy, and per-state persistence are displayed
- AND exit code 0

### R2: State Adoption — CLI

`trady-ai calibrate adopt --domain PM-5M --states 4 --generator volatility` SHALL:
1. Validate that `--states` is ≥ 2 and a StateGenerator exists for `--generator`
2. Display a summary of what will change
3. Require explicit `--confirm` flag to proceed
4. Persist adopted configuration with provenance
5. Exit 0 on success, exit 1 on validation failure or missing `--confirm`

#### Scenario: Adoption requires explicit confirmation

- GIVEN `calibrate adopt --domain PM-5M --states 5 --generator directional`
- WHEN `--confirm` is NOT provided
- THEN summary is displayed and exit code 1 — no changes applied

#### Scenario: Adoption persists with provenance

- GIVEN `calibrate adopt --domain PM-5M --states 4 --generator volatility --confirm`
- WHEN command runs successfully
- THEN adoption record written with timestamp, operator, evidence_ref, states, generator
- AND exit code 0

### R3: Immutable Provenance

The `calibration_adoptions` table SHALL contain: `id` (PK), `domain`, `strategy_name`,
`states` (int), `generator` (str), `evidence_report_ref` (str), `operator` (str),
`adopted_at` (ISO-8601), `reason` (TEXT). Rows are append-only — no UPDATE, no DELETE.

#### Scenario: Adoption record is append-only

- GIVEN existing adoption for PM-5M/directional_persistence
- WHEN a new adoption is recorded (different |S| or generator)
- THEN both rows exist — the old record is preserved

### R4: Validation Before Adoption

Before persisting, the system SHALL verify: (a) `|S|` ≥ 2, (b) a `StateGenerator`
implementation exists for the requested generator name, (c) `evidence_report_ref`
references a valid evidence report. Failures SHALL produce clear error messages.

#### Scenario: Invalid generator name rejected

- GIVEN `calibrate adopt --generator nonexistent`
- WHEN validation runs
- THEN error: "Unknown generator 'nonexistent'. Available: directional, volatility"

### R5: Review Thresholds [MODIFIED]

Calibration readiness SHALL additionally consider NEUTRAL state rate from snapshots. A domain SHALL be `ready_for_calibration` when: >=30 reflection_reports AND NEUTRAL rate < 50% across the period. The `reflection_config.review_threshold_days` key SHALL accept a NEUTRAL rate target via `review_neutral_rate_max` (default: 0.50).

(Previously: readiness based solely on report count; no NEUTRAL rate check.)

#### Scenario: Flag raised at Day 30

- GIVEN 30 distinct days with reflection_reports, threshold=30
- WHEN `_check_calibration_readiness()` runs
- THEN returns "ready_for_calibration"

#### Scenario: NEUTRAL rate triggers recalibration

- GIVEN 30 reports, NEUTRAL rate=72%
- WHEN `_check_calibration_readiness()` runs
- THEN returns `needs_recalibration` with reason: "NEUTRAL rate 72% exceeds max 50%"

### REQ-MC-009: Architecture Contract Amendment

Before any code change, the Architecture Contract SHALL be amended: §28 Amendment Log entry documenting threshold methodology change (0.1% → ATR-based), and §29 Documented Deviation D-003 for crypto domain measurement recalibration. Amendment MUST precede code changes (GO condition 1).

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Amendment entry | Contract v2.0, §28 empty | Amend: threshold methodology, D-003 | §28 row: "v2.0 → v2.1: ATR-based threshold, D-003 measurement recalibration" |
| §29 deviation | Contract v2.0, §29 has D-001, D-002 | D-003 documented | D-003 entry: "0.1% threshold calibrated for Polymarket sports; crypto requires ATR-based measurement" |
| Amendment before code | Code PR opened without amendment | PRE_FLIGHT contract check | CRITICAL violation: "Architecture Contract amendment required before code changes" |

### REQ-MC-014: Calibrate Review with Variable Thresholds

`calibrate review` SHALL display the effective threshold used per snapshot. When snapshots have different `threshold_pct` values (variable ATR-derived thresholds), the review MUST show the range: min, max, mean across all snapshots in the review window.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Variable thresholds | 30 snapshots, τ range [0.0008, 0.0035] | `calibrate review --domain BINANCE-SPOT` | displays "Threshold range: 0.0008–0.0035 (mean: 0.0018)" |
| Single snapshot | 1 snapshot, τ=0.0012 | `calibrate review` | displays "Threshold: 0.0012" |
| Empty DB | No snapshots for domain | `calibrate review` | displays "No snapshots available for BINANCE-SPOT" |
