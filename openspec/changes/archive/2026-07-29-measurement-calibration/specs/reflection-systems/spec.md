# Delta for Reflection Systems

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: ReflectionEngine Orchestration (MODIFIED)

The engine pipeline SHALL include a new `persist_snapshot()` step after analyzers run and before report assembly. The engine MUST accept `ExecutionResult` as optional parameter to `reflect()`. Analyzer pipeline order unchanged.

(Previously: no snapshot persistence in ReflectionEngine pipeline.)

- GIVEN `reflect(scope="session", domain="PM-5M", execution_result=result)` → WHEN analyzers complete → THEN `persist_snapshot(result)` runs before report assembly
- GIVEN `reflect()` called without `execution_result` → WHEN no snapshot data available → THEN snapshot step skipped silently, report assembled normally
