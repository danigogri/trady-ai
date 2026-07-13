# Paper Trading Specification

## Purpose

Operational sequencer for capture → execute → reflect → verify over a 30-day dry_run window. Coordinates existing services via direct Python import. No new business logic, analytical capability, governance, or execution authority.

## State Machine

```
IDLE → PRE_FLIGHT → CAPTURING → EXECUTING → REFLECTING → VERIFYING → BUNDLING → COMPLETE
         ↓              ↓            ↓            ↓
       ERROR          ERROR        ERROR        ERROR
```

## Requirements

### REQ-PT-001: Session Lifecycle

`PaperTradingSession` at `src/trady_ai/paper_trading/session.py`. Stateless. Single invocation of `run_session(scope, domain, market_ids, non_interactive=False) → SessionReport` traverses all states sequentially. State machine is internal sequencing, not persisted. Exception → ERROR.

| Transition | Validation | Failure |
|---|---|---|
| → PRE_FLIGHT | Contracts evaluated + reconstruction: detect first incomplete stage from persisted evidence | ERROR |
| → CAPTURING | DRY_RUN_ENFORCED, NO_REAL_FUNDS, DB ok | ERROR |
| → EXECUTING | event_store ≥1 new event | ERROR |
| → REFLECTING | ExecutionResult persisted | ERROR |
| → VERIFYING | reflection_report persisted | ERROR |
| → BUNDLING | Evidence completeness ok | ERROR |
| → COMPLETE | Manifest + checksums valid | ERROR |

### REQ-PT-002: Operational Contracts

Validated in `contracts.py`. Violation → `ContractViolation(severity, name, detail)`.

| Contract | Validates | When | Severity |
|---|---|---|---|
| DRY_RUN_ENFORCED | `validate_execution_secrets()` passes | PRE_FLIGHT | CRITICAL |
| NO_REAL_FUNDS | `place_order()` never called; trades dry_run=1 | PRE_FLIGHT + VERIFYING | CRITICAL |
| TEMPORAL_INTEGRITY | No duplicate session same day+domain | PRE_FLIGHT | CRITICAL |
| EVIDENCE_COMPLETENESS | reflection_report exists | VERIFYING | CRITICAL |
| DETERMINISTIC_REPRODUCIBILITY | `verify_replay()` passes | VERIFYING | WARNING |
| REFLECTION_ISOLATION | Reflection writes only reflection tables | VERIFYING | CRITICAL |

### REQ-PT-003: Operational Isolation

MUST NOT: (1) make strategy decisions, (2) interpret signals, (3) modify parameters, (4) generate proposals, (5) perform reasoning, (6) assume governance authority. Enforced via import boundary: session module MUST NOT import `strategies`, `intelligence`, `governance`. Violation: CRITICAL.

### REQ-PT-004: Service Coordination

Direct Python import only: `EventCapture.start()/stop()`, `ExecutionEngine.run_from_store(strategy, since_seq)`, `ReflectionEngine.reflect(scope, domain, mode)`.

### REQ-PT-005: Evidence Bundling

Per-session bundle at `paper_trading/dia-NNN/`: `manifest.json` (day, domain, timestamps, artifacts, SHA-256), `session_report.json` (FK → reflection_reports.id), `contracts.json` (validation results).

### REQ-PT-006: CLI Interface

`trady-ai paper-trade` group: `session --scope daily --domain PM-5M [--non-interactive]`, `status` (day N/30), `bundle --day N`.

### REQ-PT-007: Error Handling

Capture fail → ERROR, retryable. Execute fail → ERROR, events preserved, retry same since_seq. Reflect fail → ERROR, execution preserved, retry. Duplicate → PRE_FLIGHT rejects. Interrupted → reconstruct operational state from persisted evidence, continue from first incomplete stage.

### REQ-PT-008: 30-Day Lifecycle

Day 0: pre-flight. Days 1-30: daily cycle. Day 30: `_check_calibration_readiness()` → `ready_for_calibration`. Valid day: ≥1 reflection_report for that date.

## Scenarios

### S1: Full session — REQ-PT-001
- GIVEN dry_run=true, DB ok, no prior session today
- WHEN `run_session("daily", "PM-5M", ["0x123"])`
- THEN all states traversed, returns SessionReport, bundle written with valid checksums

### S2: Pre-flight dry_run disabled — REQ-PT-002
- GIVEN execution_mode="live"
- WHEN `run_session()` called → DRY_RUN_ENFORCED fails → ERROR

### S3: Pre-flight DB unreachable — REQ-PT-002
- GIVEN DB locked/missing → PRE_FLIGHT fails → ERROR

### S4: Capture API down — REQ-PT-007
- GIVEN WS fails, zero events → CAPTURING → ERROR, retryable

### S5: Execute error — REQ-PT-007
- GIVEN engine raises → EXECUTING → ERROR, events preserved, deterministic retry

### S6: Duplicate session — REQ-PT-002
- GIVEN session exists today for "PM-5M" → TEMPORAL_INTEGRITY fails → returns new ERROR SessionReport with TEMPORAL_INTEGRITY violation

### S7: Evidence gap — REQ-PT-002
- GIVEN no reflection_report after reflect → VERIFYING → CRITICAL ERROR

### S8: Non-interactive — REQ-PT-006
- GIVEN `--non-interactive` → no prompts, exit 0/1 on COMPLETE/ERROR

### S9: Status — REQ-PT-006
- GIVEN 12 sessions across 12 days → `status` shows "Day 12/30"

### S10: Bundle completed day — REQ-PT-005
- GIVEN day 5 complete → `bundle --day 5` → manifest.json with checksums

### S11: Bundle incomplete day — REQ-PT-005
- GIVEN day 8 missing report → `bundle --day 8` → fails, no bundle

### S12: 30-day end gate — REQ-PT-008
- GIVEN 30 distinct days, ≥30 reports → VERIFYING → calibration_state = "ready_for_calibration"
