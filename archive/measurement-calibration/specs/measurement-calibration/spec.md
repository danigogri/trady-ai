# Measurement Calibration Specification

**Domain**: measurement-calibration | **Type**: New
**Baseline**: Closure Report §7, §6 | **RFC**: RFC-004, RFC-007

## Purpose

Replace frozen 0.1% threshold with ATR-based deterministic calibration for crypto tick data. Assign state classification (UP/DOWN/NEUTRAL) to Evidence Clock as measurement (D2, D3).

**Deterministic boundary**: ATR = pure arithmetic, frozen α. No AI/ML. No mid-phase changes.

---

## Requirements

| ID | Requirement | Scenarios |
|---|---|---|
| **REQ-MC-001** | Evidence Clock SHALL compute threshold as `τ = α × ATR_N / last_price`. Same tick history → identical τ. ATR window slides per tick. | Happy: N=20 ticks, α=1.5 → τ computed. Edge: Empty buffer → τ=0, classify NEUTRAL. Edge: Volatility spike → τ adapts within N ticks. |
| **REQ-MC-002** | α SHALL be operator-adopted before Day 0. Default=2.0, range [0.5, 5.0]. Version-controlled. Adjustable only at review windows (C4). | Happy: `calibrate adopt --alpha 1.5 --confirm` → config frozen. Error: α=0.0 → rejected. Edge: Mid-phase change → WARNING, reverted. |
| **REQ-MC-003** | `MarketStateTracker` SHALL classify per tick as UP/DOWN/NEUTRAL using ATR threshold. First tick per market → NEUTRAL. | Happy: Δp > τ → UP. Edge: Δp within τ → NEUTRAL. Edge: First tick → NEUTRAL, `previous_state=None`. |
| **REQ-MC-004** | `event_store` SHALL carry `classified_state` column. Populated atomically with each captured event. MUST NOT be computed downstream. | Happy: Capture → row has `classified_state="UP"`. Edge: Empty DB → column populated, not NULL. |
| **REQ-MC-010** | Operator SHALL run pre-Day-0 calibration pilot against testnet data to determine N and α. Output: frozen `RuntimeConfig`. | Happy: Pilot produces evidence_report with NEUTRAL rate. Edge: NEUTRAL > 50% → operator adjusts α, re-runs. |
| **REQ-MC-011** | Threshold methodology (N, α) SHALL NOT change during confirmatory phase. Adjustments only at review windows with Contract amendment. | Happy: Frozen throughout. Edge: Config drift → WARNING, reverted. Edge: Review window → §28 logged, α updated. |
| **REQ-MC-012** | Same tick history + same (α, N) SHALL produce identical state sequences. Pure function — no external state, no hidden deps. | Happy: Two runs, same ticks → identical sequences. Edge: Different α → sequences MAY differ; each internally consistent. |
| **REQ-MC-013** | All 199 existing tests SHALL pass after migration. Tests asserting `threshold_pct=0.001` updated to assert state labels, not constant. | Happy: Full suite → 199 pass, ≥90% coverage. Edge: Snapshot JSON now includes `alpha`, `atr_period`. |

---

## Constraints (from Discovery Closure)

- C1: No new clocks — Evidence Clock absorbs measurement
- C2: Three states (UP/DOWN/NEUTRAL) fixed
- C3: No AI/ML — pure arithmetic threshold
- C4: No mid-phase threshold changes in confirmatory
- C5: Single unified snapshot artifact (`created_by` column)
- C6: Session does not own persistence — delegate to Reflection Clock
