# Delta for Strategy Infrastructure

## MODIFIED Requirements

### R6: Lifecycle Hooks [MODIFIED]

`on_snapshot()` hook SHALL produce serializable state dictionary (unchanged). The hook MUST NOT call `persist_strategy_snapshot()` — persistence is delegated to Reflection Clock (C6, D7). The hook remains available for internal state export.

(Previously: `on_snapshot()` was consumed by strategy's own `snapshot()` method which called `persist_strategy_snapshot()` directly.)

- GIVEN `MarkovPersistenceEngine.on_snapshot()` → WHEN called → THEN returns dict with transition_counts, state_counts; NO DB write
- GIVEN strategy `snapshot()` method → WHEN called → THEN deprecated: emits DeprecationWarning, returns data dict without persisting

## ADDED Requirements

### REQ-MC-008: Snapshot Schema with Provenance Column

`strategy_snapshots` table SHALL add `created_by TEXT NOT NULL DEFAULT 'strategy'` column. Valid values: `"strategy"` (legacy), `"reflection_engine"` (post-migration). Existing rows retain `"strategy"`. New rows from ReflectionEngine SHALL write `"reflection_engine"`.

| Scenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Reflection persists snapshot | ExecutionResult from session | `persist_strategy_snapshot(created_by="reflection_engine")` | row has `created_by="reflection_engine"` |
| Legacy call path (deprecated) | Strategy's `snapshot()` not yet migrated | old code path | row has `created_by="strategy"` (default) |
| Migration validation | DB with mixed provenance | query `SELECT DISTINCT created_by` | both values present; `reflection_engine` rows growing |
| Backward compatible | 199 existing tests read `strategy_snapshots` | tests query all columns | `created_by` column transparent; no test breakage |
