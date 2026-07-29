# Delta for Paper Trading

## MODIFIED Requirements

### REQ-PT-001: Session Lifecycle [MODIFIED]

`PaperTradingSession` — REFLECTING stage SHALL delegate strategy snapshot persistence to Reflection Clock. Session MUST NOT call `persist_strategy_snapshot()` directly (C6, D7). Per-clock reconstruction unchanged.

(Previously: REFLECTING stage did not create strategy snapshots; snapshots were created mid-stream by strategy's `snapshot()` hook.)

| Transition | Validation |
|---|---|
| -> REFLECTING | ExecutionResult persisted |
| -> REFLECTING | ReflectionEngine creates snapshot from ExecutionResult data (delegated) |

- GIVEN ExecutionResult with transition_counts → WHEN session enters REFLECTING → THEN ReflectionEngine persists snapshot; session never imports `core.persistence.persist_strategy_snapshot`

### REQ-PT-005: Evidence Bundling [MODIFIED]

Session bundles in `dia-NNN/sesion-MMM/` SHALL include `strategy_snapshot.json` when a snapshot was persisted during REFLECTING. Manifest SHALL include SHA-256 of snapshot artifact.

(Previously: bundles did not include snapshot artifacts.)

- GIVEN snapshot persisted during REFLECTING → WHEN bundling → THEN `dia-001/sesion-001/strategy_snapshot.json` present with checksum in manifest
- GIVEN no snapshot (first session, empty DB) → WHEN bundling → THEN no `strategy_snapshot.json`; manifest unchanged

## ADDED Requirements

### REQ-MC-005: Snapshot Creation During REFLECTING Stage

Session SHALL delegate snapshot persistence to ReflectionEngine during the REFLECTING stage. Delegation occurs after analyzers complete, before report assembly. Strategy's internal `on_snapshot()` hook MAY still produce data but MUST NOT call `persist_strategy_snapshot()` directly.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Normal snapshot | ExecutionResult with transition_counts after EXECUTING | Session enters REFLECTING | ReflectionEngine persists snapshot with `created_by="reflection_engine"` |
| Reflection failure | Engine exception during snapshot persist | Session REFLECTING stage | Session enters ERROR state; snapshot not persisted, state preserved for retry |
| First session | Empty DB, no prior snapshot | ReflectionEngine checks existing | Skips idempotency check; persists first snapshot |
