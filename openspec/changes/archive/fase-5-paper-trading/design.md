# Design: Fase 5 — Paper Trading (Operational Phase)

## Technical Approach

Stateless operational sequencer (`PaperTradingSession.run_session()`) that orchestrates existing services (EventCapture, ExecutionEngine, ReflectionEngine) via direct Python import. Internal state machine (PRE_FLIGHT→CAPTURING→EXECUTING→REFLECTING→VERIFYING→BUNDLING→COMPLETE) runs in a single invocation. Session completion is derived from persisted evidence — no new session table. Per-session evidence bundles are regenerable deterministic exports from DB.

Architectural boundary: **operational sequencing only**. Zero business logic, signal modification, or parameter adjustment. The 6 MUST NOT prohibitions from the Operational Isolation Contract are enforced via import boundary checks in `contracts.py`.

## Architecture Decisions

### ADR-1: Stateless Operational Sequencer

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Stateful session manager with persistent automaton | Trackable, but adds table+complexity for a bounded 30-day window | **Rejected** — mirrors `ReflectionEngine.reflect()` stateless pattern |
| Stateless `run_session()` single invocation | Simpler, no new table, deterministic reconstruction from evidence | **Chosen** — state machine is internal sequencing logic, not persisted |

### ADR-2: State Derivation from Evidence (No Session Table)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `paper_trading_sessions` table | Audit trail, but new schema + migration + sync burden | **Rejected** — violates "no new DB tables" constraint |
| Derive completion from existing data | Event count for capture, trade count for execution, report existence for reflection | **Chosen** — `reflection_reports` is the authoritative "session completed" signal |

### ADR-3: Evidence Bundle as Deterministic Export

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Append-only bundle per session | Simple append, but stale on DB changes | **Rejected** — violates determinism |
| Regenerable from DB via `bundle --day N` | Always fresh, verifiable, no drift between bundle and DB state | **Chosen** — DB is source of truth, bundle is portable snapshot |

### ADR-4: Session Reconstruction from Evidence

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Checkpoint/restore with persisted state | Resume at exact byte, but fragile across schema changes | **Rejected** — opaque, non-deterministic |
| Detect first incomplete stage from DB queries | Deterministic, auditable, no hidden state | **Chosen** — "what data exists = what was completed" |

## Data Flow

```
run_session("daily", "PM-5M", ["0x123"])
  │
  ├─ PRE_FLIGHT
  │   ├─ contracts.dry_run_enforced()      ← validate_execution_secrets()
  │   ├─ contracts.no_real_funds()         ← SELECT dry_run=0 FROM trades
  │   ├─ contracts.temporal_integrity()    ← SELECT FROM reflection_reports today
  │   └─ reconstruct()                     ← detect first incomplete stage
  │
  ├─ CAPTURING
  │   ├─ EventCapture(adapter, db).start(market_ids)
  │   ├─ [interactive] wait for Ctrl+C
  │   ├─ [non-interactive] timed capture
  │   └─ EventCapture.stop()
  │
  ├─ EXECUTING
  │   ├─ MarkovStrategy(warmup, threshold)
  │   ├─ ExecutionEngine(config, db, dry_run=True)
  │   └─ engine.run_from_store(strategy, since_seq)
  │
  ├─ REFLECTING
  │   ├─ ReflectionEngine(db, analyzers…)
  │   └─ engine.reflect(scope, domain, mode="dry_run")
  │
  ├─ VERIFYING
  │   ├─ contracts.no_real_funds()              ← re-verify no live trades created
  │   ├─ contracts.evidence_completeness()      ← reflection_report exists
  │   ├─ contracts.deterministic_reproducibility()  ← replay verify
  │   └─ contracts.reflection_isolation()       ← reflection tables only
  │
  ├─ BUNDLING
  │   └─ EvidenceBundler.bundle(report) → paper_trading/dia-NNN/
  │
  └─ COMPLETE → SessionReport
```

## State Derivation Logic

Reconstruction = check existing data to skip completed stages:

| Stage | Check | Data Source |
|-------|-------|-------------|
| CAPTURING | `COUNT(*) FROM event_store` for today > 0 | `event_store.timestamp` |
| EXECUTING | `COUNT(*) FROM trades` for today > 0 | `trades.timestamp` |
| REFLECTING | `COUNT(*) FROM reflection_reports WHERE domain AND today` | `reflection_reports.period_start` |
| BUNDLING | Manifest file exists at `paper_trading/dia-NNN/manifest.json` | Filesystem check |

Stage executed if its check returns zero — otherwise skipped.

## Component Design

### `session.py` — PaperTradingSession

- **Responsibility**: Coordinate the full session lifecycle in one call.
- **Public**: `run_session(scope, domain, market_ids, non_interactive=False) → SessionReport`
- **Internal state machine**: PRE_FLIGHT → CAPTURING → EXECUTING → REFLECTING → VERIFYING → BUNDLING → COMPLETE
- **Reconstruction**: At PRE_FLIGHT, run state derivation checks → build skip list.
- **Pattern**: Matches `ReflectionEngine.reflect()` — constructor takes `db`, one public method per cycle.
- **Import boundary**: MUST NOT import `strategies`, `intelligence`, or `governance` modules.

### `contracts.py` — OperationalContracts

- **Responsibility**: Validate 6 operational invariants per REQ-PT-002.
- **Each contract** is a function returning `list[ContractViolation]` (empty = pass).
- Severity model: `CRITICAL` halts session (PRE_FLIGHT/VERIFYING), `WARNING` logged only.

### `bundler.py` — EvidenceBundler

- **Responsibility**: Produce/reproduce portable evidence bundles.
- **`bundle(report)`**: Query DB for today's artifacts, compute SHA-256, write `manifest.json` + `session_report.json` + `contracts.json`.
- **`regenerate_bundle(day, domain)`**: Reconstruct from DB — same logic as `bundle()` but reads from historical data.
- Bundle path: `paper_trading/dia-NNN/` (relative to project root or configurable base).

### `models.py`

```python
@dataclass
class SessionReport:
    day: int; domain: str; event_count: int; trade_count: int
    reflection_report_id: int | None; contract_results: list[ContractViolation]
    stage_timestamps: dict[str, str]; calibration_state: str

@dataclass
class SessionManifest:
    day: int; domain: str; created_at: str; artifact_checksums: dict[str, str]

@dataclass
class ContractViolation:
    contract_name: str; severity: str  # CRITICAL | WARNING
    detail: str; timestamp: str

class SessionState(StrEnum):
    IDLE = "idle"; PRE_FLIGHT = "pre_flight"; CAPTURING = "capturing"
    EXECUTING = "executing"; REFLECTING = "reflecting"
    VERIFYING = "verifying"; BUNDLING = "bundling"
    COMPLETE = "complete"; ERROR = "error"
```

## Error Handling (per Spec Scenarios)

| Scenario | Failure Point | Behavior |
|----------|--------------|----------|
| S2 — dry_run disabled | PRE_FLIGHT | CRITICAL violation → ERROR, halt |
| S3 — DB unreachable | PRE_FLIGHT | Exception → ERROR, halt |
| S4 — Capture API down | CAPTURING | Exception → ERROR, events preserved |
| S5 — Engine error | EXECUTING | Exception → ERROR, events preserved, retryable same `since_seq` |
| S6 — Duplicate today | PRE_FLIGHT | TEMPORAL_INTEGRITY violation → return new ERROR SessionReport |
| S7 — Missing reflection_report | VERIFYING | CRITICAL evidence_completeness failure → ERROR stage |

## CLI Design

```
trady-ai paper-trade session --scope daily --domain PM-5M --markets 0x123 [--non-interactive]
trady-ai paper-trade status
trady-ai paper-trade bundle --day N
```

- `paper-trade` = Click group (lazy imports, per existing pattern)
- `session` = Click command, calls `PaperTradingSession.run_session()`
- `status` = Query `reflection_reports` + `trades` + `event_store` → show day N/30
- `bundle` = Calls `EvidenceBundler.regenerate_bundle(day, domain)`
- Exit codes: 0 = COMPLETE, 1 = ERROR (per S8)

## File Changes

| File | Action | Lines |
|------|--------|-------|
| `src/trady_ai/paper_trading/__init__.py` | Create | 1 |
| `src/trady_ai/paper_trading/models.py` | Create | ~50 |
| `src/trady_ai/paper_trading/session.py` | Create | ~140 |
| `src/trady_ai/paper_trading/contracts.py` | Create | ~100 |
| `src/trady_ai/paper_trading/bundler.py` | Create | ~120 |
| `src/trady_ai/cli/main.py` | Modify | ~+50 (paper-trade group + 3 commands) |

**Total**: ~460 new lines — within 500-line budget.

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | Contracts (each violation scenario), models, bundler | Pure function tests, no DB |
| Integration | Full S1 session (mock external services), S2-S7 error paths | Test with SQLite :memory:, mock PolymarketAdapter |
| CLI | Each command exit code + output format | Click CliRunner |

## Migration / Rollout

No migration required. No new DB tables, no schema changes. The `paper_trading/` bundle directory is created on first `bundle` call. Rollback = delete `paper_trading/` directory + revert `main.py`.

## Open Questions

None resolved by pre-design decisions. Proceed to Tasks.
