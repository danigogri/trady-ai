# Exploration: Fase 4 — Reflection Systems (RFC-004)

**Date**: 2026-07-11  
**Phase**: Fase 4 — Reflection Systems  
**RFC**: RFC-004-REFLECTION-SYSTEMS-ARCHITECTURE  
**Status**: Exploration complete — ready for proposal

---

## Current State

### Codebase Map

**Reflection layer (`src/trady_ai/reflection/`)**:
- Exists as empty placeholder (`__init__.py` with docstring only)
- No implementation yet — clean slate

**Core layer (`src/trady_ai/core/`)** — provides execution lineage:
- `models.py`: MarketInput, MarketState, Signal, Position, Trade, ExecutionDecision (Pydantic)
- `engine.py`: ExecutionEngine with 9-step tick pipeline, produces ExecutionResult
- `persistence.py`: 6 tables (market_states, signals, positions, trades, execution_log, event_store, strategy_snapshots)
- `observability.py`: `compute_summary()` — basic win_rate, PnL, drawdown stats
- `replay.py`: Deterministic replay from execution_log, verify_replay() for reproducibility
- `risk.py`: RiskEnforcer with 5 sequential checks (C0-C5)
- `state.py`: MarketStateTracker — classifies UP/DOWN/NEUTRAL
- `normalization.py`: normalize() — input validation and Decimal conversion

**Adapters layer (`src/trady_ai/adapters/`)**:
- `polymarket.py`: PolymarketAdapter (stateless REST/WS), EventCapture (daemon thread capture)
- Event store schema (9 columns):
  ```
  seq INTEGER PRIMARY KEY AUTOINCREMENT
  event_id TEXT NOT NULL UNIQUE
  market_id TEXT NOT NULL
  price TEXT NOT NULL
  volume TEXT NOT NULL
  timestamp TEXT NOT NULL
  event_type TEXT NOT NULL
  source TEXT NOT NULL DEFAULT 'polymarket'
  raw_payload TEXT NOT NULL
  captured_at TEXT NOT NULL
  ```
- `append_event()`: dedup via event_id UNIQUE, returns seq or None
- `get_events()`: reads as MarketInput list with since_seq cursor
- `get_max_seq()`, `count_events()`: utility queries

**Strategies layer (`src/trady_ai/strategies/`)**:
- `base.py`: StrategyBase ABC — evaluate(), update(), is_ready(), parameters(), lifecycle hooks
- `registry.py`: StrategyRegistry — singleton per (domain, name), factory-based
- `markov/persistence.py`: 3 variants:
  - MarkovPersistenceEngine: 3×3 transition matrix (UP/DOWN/NEUTRAL → LONG/SHORT/NEUTRAL)
  - DirectionalPersistence: alias for semantic clarity
  - VolatilityPersistence: HIGH/LOW/STABLE volatility regime classification
- Snapshot/restore: `snapshot()` persists to strategy_snapshots table, `restore()` reconstructs from DB
- strategy_snapshots schema:
  ```
  id INTEGER PRIMARY KEY AUTOINCREMENT
  strategy_name TEXT NOT NULL
  domain TEXT NOT NULL
  tick_number INTEGER NOT NULL
  transition_counts TEXT NOT NULL  -- JSON 3×3 matrix
  state_counts TEXT NOT NULL       -- JSON length-3 list
  warmup_ticks INTEGER NOT NULL
  threshold_pct TEXT NOT NULL
  snapshot_at TEXT NOT NULL
  UNIQUE(strategy_name, domain, tick_number)
  ```

**Governance layer (`src/trady_ai/governance/`)**:
- Empty placeholder (`__init__.py` only) — Fase 7 scope

**Config layer (`src/trady_ai/config/`)**:
- `runtime_config.py`: RuntimeConfig (threshold_pct, warmup_ticks, position_size, stop_loss_pct, execution_mode)
- `settings.py`: Settings (environment, API credentials, paths)

### RFC-004 Summary

**Core Principle**: "Reflection analyzes execution. It does not control execution."

**What Reflection IS**:
- Analytical, post-execution, bounded, observational, proposal-oriented
- Evaluates: trade outcomes, signal quality, strategy stability, parameter consistency, drift patterns, execution anomalies
- Produces: summaries, evaluations, proposals, anomaly reports, bounded recommendations

**What Reflection is NOT**:
- Execution engine, orchestration framework, autonomous governance system
- Runtime mutation system, unrestricted optimization, self-modifying runtime

**Proposal Lifecycle** (mandatory separation):
```
Observation → Evaluation → Proposal → Governance Review → Controlled Approval → Deterministic Deployment
```

**Drift Detection**:
- Detects: statistical degradation, strategy instability, execution anomalies, parameter drift
- Detection is OBSERVATIONAL ONLY — no autonomous correction, no hidden recalibration

**Reflection Scheduling**:
- Bounded evaluation windows: session, daily, weekly, monthly, domain-level
- Rejects: continuous uncontrolled adaptation, runtime self-modification, invisible optimization loops

**Safety Boundaries** (RFC-004 + RFC-000):
- MUST NOT execute trades
- MUST NOT mutate production systems
- MUST NOT bypass governance
- MUST NOT rewrite frozen contracts
- MUST NOT modify execution behavior directly
- MUST remain: bounded, reviewable, auditable, governance-constrained
- Fail-fast mandatory — no silent degradation, no hidden proposal mutation

**Data Dependencies** (what Reflection consumes):
- Execution lineage: execution_log, signals, trades, positions
- Observability outputs: compute_summary() stats
- Event store: event_store (raw market data)
- Strategy data: strategy_snapshots (transition matrices, state counts)

**Integration Points**:
- Reads from Core tables (market_states, signals, positions, trades, execution_log)
- Reads from event_store (Fase 2)
- Reads from strategy_snapshots (Fase 3)
- Does NOT inject into Core execution pipeline
- Does NOT mutate strategy state
- Proposals go to Governance (Fase 7) — not implemented yet

### Gap Analysis

**What needs to be built from scratch**:
1. **Reflection module structure** (`src/trady_ai/reflection/`):
   - Analyzers: trade outcome analysis, signal quality evaluation, strategy performance
   - Drift detectors: statistical degradation, parameter drift, execution anomalies
   - Proposal generators: bounded parameter adjustments, strategy recommendations
   - Reflection reports: structured output (summaries, evaluations, anomaly reports)

2. **Reflection scheduling** (session/daily/weekly/monthly windows):
   - Trigger mechanism (post-execution, time-based, manual)
   - Window boundary detection
   - Reflection session lifecycle

3. **Proposal data model**:
   - Proposal schema (bounded, reviewable, auditable, reversible, attributable)
   - Proposal storage (separate from execution tables)
   - Proposal status tracking (pending, reviewed, approved, rejected, deployed)

4. **Drift detection algorithms**:
   - Statistical tests for distribution shift
   - Threshold-based anomaly detection
   - Strategy stability metrics

5. **Reflection persistence**:
   - Tables for reflection results, proposals, drift reports
   - Query APIs for historical reflection data

**What existing code can be reused**:
- `core/observability.py`: `compute_summary()` — basic stats (win_rate, PnL, drawdown)
- `core/persistence.py`: all query functions (load_execution_log, get_events, load_latest_snapshot)
- `core/replay.py`: deterministic replay for what-if analysis
- `strategies/markov/persistence.py`: snapshot/restore for strategy state comparison
- Event store: rich raw data for analysis (raw_payload, timestamps, prices)

**What existing code needs extension points**:
- `core/observability.py`: may need more granular stats (per-strategy, per-domain, time-series)
- `core/persistence.py`: may need new query functions for reflection (time-bounded queries, aggregation)
- CLI (`cli/main.py`): reflection commands (analyze, report, propose)
- No existing code needs modification — Reflection is purely additive (read-only consumer)

### Risks & Questions

**Ambiguities in RFC-004**:
1. **Proposal format**: RFC-004 says proposals must be "bounded, reviewable, auditable, reversible, attributable" but does NOT define the schema. SDD must define:
   - What constitutes a "bounded" proposal? (parameter range? strategy swap? config change?)
   - How are proposals versioned and tracked?
   - What is the proposal approval workflow? (Governance is Fase 7 — not built yet)

2. **Drift detection algorithms**: RFC-004 mentions "statistical degradation, strategy instability" but does NOT specify:
   - Which statistical tests? (KS test, chi-square, rolling window comparison?)
   - What thresholds trigger drift alerts?
   - How to handle non-stationary time series?

3. **Reflection scheduling**: RFC-004 mentions "session, daily, weekly, monthly" windows but does NOT specify:
   - How are windows triggered? (cron, manual, post-execution hook?)
   - What happens if reflection fails mid-window?
   - Can windows overlap? (e.g., daily reflection running while session reflection is active)

4. **Intelligence integration**: RFC-004 says Reflection "may use Hermes, Pythy, GPT, Claude, local models" but:
   - Intelligence is Fase 5 — not built yet
   - How does Reflection work without intelligence in Fase 4? (pure statistical analysis?)
   - Is Fase 4 reflection deterministic-only, or can it use external LLMs?

5. **Proposal deployment**: RFC-004 lifecycle ends at "Controlled Approval → Deterministic Deployment" but:
   - Deployment mechanism is not defined (manual config change? automated rollback?)
   - How to verify proposal was deployed correctly?
   - What if proposal causes regression? (rollback plan?)

**Potential conflicts with existing architecture**:
1. **Read-only constraint**: Reflection MUST NOT mutate Core or strategy state. This is clear, but:
   - Can Reflection write to its own tables? (yes — reflection_results, proposals, drift_reports)
   - Can Reflection read from event_store raw_payload? (yes — Fase 2 spec explicitly allows this)
   - Can Reflection call strategy methods? (NO — strategies are isolated, Reflection observes only)

2. **Data volume**: event_store can grow large (high-frequency WS events). Reflection queries must:
   - Use time-bounded queries (WHERE timestamp BETWEEN x AND y)
   - Avoid full-table scans
   - Consider indexing (timestamp, market_id, event_type)

3. **Determinism**: Reflection analysis must be reproducible. This means:
   - No random seeds in drift detection algorithms
   - Deterministic ordering of results (ORDER BY timestamp, seq)
   - Versioned algorithms (algorithm v1 vs v2 may produce different results)

**Performance considerations**:
1. **Event store size**: Polymarket WS can produce thousands of events per hour. Reflection queries over large time windows may be slow.
   - Mitigation: time-bounded queries, indexed columns, batch processing
2. **Snapshot comparison**: Comparing strategy_snapshots across time requires loading JSON and computing matrix differences.
   - Mitigation: cache parsed snapshots, incremental comparison
3. **Reflection frequency**: If reflection runs after every execution session, it may slow down the pipeline.
   - Mitigation: async reflection (post-execution), separate process/thread

### Recommendations

**Suggested implementation order**:

**Option A: Minimal Viable Reflection (recommended)**
1. **Reflection data model** (1-2 days):
   - Define proposal schema (bounded, reviewable, auditable)
   - Create reflection tables (reflection_results, proposals, drift_reports)
   - Query APIs for reflection data

2. **Basic analyzers** (2-3 days):
   - Trade outcome analysis (win/loss, PnL distribution, holding time)
   - Signal quality evaluation (confidence calibration, direction accuracy)
   - Strategy performance (per-strategy, per-domain stats)

3. **Drift detection v1** (2-3 days):
   - Simple threshold-based detection (rolling window mean/stddev)
   - Parameter drift (compare current vs baseline strategy_snapshots)
   - Execution anomaly detection (unusual trade frequency, PnL spikes)

4. **Proposal generator v1** (1-2 days):
   - Bounded parameter proposals (warmup_ticks, threshold_pct adjustments)
   - Proposal storage and status tracking
   - Proposal review interface (CLI command or report)

5. **Reflection scheduling** (1 day):
   - Post-execution reflection trigger
   - Session/daily/weekly window detection
   - Reflection report generation

**Total effort**: 7-11 days (one change, phased tasks)

**Option B: Full Reflection System**
- Includes intelligence integration (LLM-assisted analysis), advanced drift detection (statistical tests), proposal deployment automation
- Effort: 15-20 days
- Risk: Overengineering before Governance (Fase 7) is built

**Recommendation**: **Option A** — minimal viable reflection that respects RFC-004 doctrine without overengineering. Fase 4 should establish the foundation (data model, basic analyzers, simple drift detection, proposal storage). Advanced features (intelligence integration, automated deployment) belong to Fase 5+ and Fase 7.

**Should this be one change or multiple?**
- **One change** with phased tasks (T1-T5 above). Rationale:
  - All components are tightly coupled (analyzers feed drift detection, drift detection feeds proposals)
  - Splitting into multiple changes would require intermediate integration points
  - One change allows atomic verification (all tests pass together)
  - Tasks are small enough to complete in one session each

**Pre-requisites before coding**:
1. **Clarify proposal schema** with user (what constitutes a "bounded" proposal?)
2. **Clarify drift detection approach** (threshold-based vs statistical tests?)
3. **Clarify reflection scheduling** (post-execution trigger vs time-based?)
4. **Decide on intelligence integration** (Fase 4 = deterministic-only, or allow LLM calls?)
5. **Review BL-018** (deferred `_last_state` persistence) — should this be fixed before Reflection analyzes snapshots?

---

## Affected Areas

- `src/trady_ai/reflection/` — new module (analyzers, drift detectors, proposal generators, reports)
- `src/trady_ai/core/persistence.py` — may need new query functions (time-bounded, aggregation)
- `src/trady_ai/core/observability.py` — may need extension (per-strategy stats, time-series)
- `src/trady_ai/cli/main.py` — reflection commands (analyze, report, propose)
- `tests/unit/test_reflection/` — new test directory
- `tests/integration/test_reflection_integration.py` — integration tests
- `openspec/specs/reflection-systems/` — new spec directory

---

## Ready for Proposal

**Yes** — exploration is complete. The orchestrator should:
1. Review this exploration report with the user
2. Clarify the 5 open questions (proposal schema, drift detection, scheduling, intelligence, BL-018)
3. Launch SDD proposal phase (sdd-propose) for Fase 4 — Reflection Systems
4. Proposal should reference RFC-004, respect RFC-000 safety doctrine, and follow Option A (minimal viable reflection)
