# Delta for Governance

## ADDED Requirements

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

## MODIFIED Requirements

### R5: Review Thresholds [MODIFIED]

Calibration readiness SHALL additionally consider NEUTRAL state rate from snapshots. A domain SHALL be `ready_for_calibration` when: >=30 reflection_reports AND NEUTRAL rate < 50% across the period. The `reflection_config.review_threshold_days` key SHALL accept a NATURAL rate target via `review_neutral_rate_max` (default: 0.50).

(Previously: readiness based solely on report count; no NEUTRAL rate check.)

- GIVEN 30 reports, NEUTRAL rate=35% → WHEN `_check_calibration_readiness()` → THEN returns `ready_for_calibration`
- GIVEN 30 reports, NEUTRAL rate=72% → WHEN checked → THEN returns `needs_recalibration` with reason: "NEUTRAL rate 72% exceeds max 50%"
