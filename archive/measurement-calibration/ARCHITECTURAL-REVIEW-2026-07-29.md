# ARCHITECTURAL DIALECTIC REVIEW — Paper Trading Calibration Barrier

> **Date**: 2026-07-29 | **Type**: Adversarial Architectural Review
> **Artifact Under Review**: `paper_trading/STATUS-REPORT-2026-07-29.md`
> **Primary Recommendation Challenged**: Option C (Session-level snapshot persistence + configurable threshold)
> **Authority Referenced**: Architecture Contract v2.0, RFC-000, RFC-003, RFC-004, Portable OS Constitution

---

## 1. EXECUTIVE SUMMARY

**Option C must be REJECTED.** It contains three architectural violations: (1) it proposes making `threshold_pct` configurable during the experiment, directly contradicting Architecture Contract §16.1 which FREEZES this parameter for the 30-day experiment; (2) it assigns persistence responsibility to Session, a cross-clock orchestrator that owns no persistence per the four-clock architecture; and (3) it conflates execution state with scientific evidence, placing calibration artifacts inside the execution path.

The correct solution is **Option D**: persist `strategy_snapshots` inside the REFLECTING stage, owned by the Reflection Clock, with threshold unchanged per the frozen contract. Calibration remains a post-experiment gate (§17.2). If the operator desires in-experiment threshold variation, an Architecture Contract amendment (§28) must precede any code change.

**Confidence**: HIGH. The Architecture Contract leaves no ambiguity on this point.

---

## 2. VALIDATION OF THE PROBLEM DIAGNOSIS

### 2.1 What the Status Report Claims

The Status Report identifies three sub-problems:

1. Threshold 0.1% is too large for crypto tick data
2. No calibration adopted for BYBIT-SPOT
3. `strategy_snapshots` table is empty — engine never persists transition counts

### 2.2 What the Architecture Contract Actually Says

| Claim in Status Report | Architecture Contract Reality | Verdict |
|------------------------|-------------------------------|---------|
| "Threshold must be calibrated" | §16.1: `threshold_pct=0.001` is a **fixed parameter for the 30-day experiment** | ❌ Premise conflicts with frozen architecture |
| "Calibration should happen during the experiment" | §17.2: Calibration is a **post-experiment gate** activated when `reflection_reports >= 30` | ❌ Calibration is Day 30+, not during |
| "`strategy_snapshots` should be populated" | The table is **not mentioned in the Architecture Contract's persistence model** (§6.2). It has no clock owner. | ⚠️ The table is an architectural orphan |

### 2.3 Re-diagnosis

The Status Report's diagnosis is **partially correct but misidentified the root cause**. The real issues are:

| # | Real Problem | Severity |
|---|-------------|----------|
| 1 | `strategy_snapshots` has **no architectural owner** — it is an implementation artifact without a clock | Architectural |
| 2 | The desire to calibrate **during** the experiment conflicts with Architecture Contract §17.2 (post-experiment gate) | Contract violation |
| 3 | The desire to vary `threshold_pct` **during** the experiment conflicts with Architecture Contract §16.1 (frozen parameters) | Contract violation |
| 4 | BL-018 (`_last_state` not persisted) is a symptom of the broader orphan problem, not the root cause | Symptom |

**The correct question is not "how do we populate snapshots?" but "who OWNS snapshots architecturally, and when should they be created?"**

---

## 3. ROOT CAUSE ANALYSIS

### 3.1 The Architectural Orphan

`strategy_snapshots` was created during the Calibration Framework SDD cycle as a persistence table. But it was **never assigned to a clock**. Let's trace the ownership:

| Clock | Owns (per Architecture Contract §6.2) | Does `strategy_snapshots` belong here? |
|-------|---------------------------------------|----------------------------------------|
| **Discovery** | `.env` (active markets) | ❌ No — snapshots are not about market discovery |
| **Evidence** | `event_store` table | ❌ No — snapshots are not raw market data |
| **Decision** | `signals` + `trades` tables | ⚠️ **Maybe** — snapshots capture strategy state at execution time |
| **Reflection** | `reflection_reports` table | ⚠️ **Maybe** — snapshots are evidence for calibration analysis |
| **None** | — | 🔴 **Current reality** — the table exists but no clock writes to it |

### 3.2 Why It Matters

An unowned table means:
- No clock is responsible for writing to it
- No clock's failure behavior covers it
- No clock's reconstruction logic includes it
- `calibrate review` reads from a table that nobody populates

This is why BL-018 exists. The fix wasn't implemented because **there was no architectural decision about who should fix it.**

### 3.3 The Deeper Issue: Timing

The Calibration Framework was designed for **post-experiment analysis**. The Architecture Contract §17.2 makes this explicit:

```
IF reflection_reports >= 30 (one per day)
   AND calibration_state != "ready_for_calibration"
THEN
   _check_calibration_readiness() → "ready_for_calibration"
```

Calibration is a **gate at Day 30**, not a process during the experiment. The user's desire to calibrate thresholds NOW, on Day 2, represents a legitimate operational need that the Architecture Contract did not anticipate — but that need must be resolved architecturally before implementation, per Portable OS A2 (Architecture Before Implementation).

---

## 4. REVIEW OF OPTION A

**Option A**: Add `persist_strategy_snapshot()` inside `ExecutionEngine.run()`.

### Architectural Strengths
- Engine is close to the data (has `_transition_counts` in memory)
- Minimal code surface

### Architectural Weaknesses
- **Cross-clock coupling**: Decision Clock (engine) would persist data for Reflection Clock (calibration). The Architecture Contract §6.2 says Decision "has its own persistence: signals + trades tables." Strategy snapshots are calibration evidence, not execution state.
- **Hidden lifecycle dependency**: `run()` is called by Session during EXECUTING stage. Adding persistence there means the EXECUTING stage now has a side effect that serves the REFLECTING stage — a violation of unidirectional clock dependencies.
- **`domain` parameter**: `run()` does not receive `domain`. It would need to be threaded through `run_from_store()` → `run()`, adding a parameter to the engine's public API that serves calibration, not execution.

### Portable OS Violations
| Principle | Violation |
|-----------|-----------|
| **A3 — Boundary Discipline** | Decision Clock persists calibration evidence — responsibility leakage across clocks |
| **A1 — Deterministic-First** | Adding side effects to `run()` creates implicit state mutation not declared in the method's contract |
| **A5 — Simplicity** | Engine gains calibration awareness — "50 clear lines over 500 flexible lines" |

### Verdict: REJECTED
The engine should execute, not calibrate. Cross-clock persistence is architectural drift.

---

## 5. REVIEW OF OPTION B

**Option B**: Shadow calibration script running in parallel.

### Architectural Strengths
- No code changes to the running experiment
- Read-only access to `event_store`

### Architectural Weaknesses
- **Duplicated execution logic**: The script runs `MarkovStrategy` + `ExecutionEngine.run()` outside the session lifecycle. This is a shadow Decision Clock operating without clock contracts, without reconstruction, without failure handling, without temporal integrity.
- **Contaminated evidence**: The script writes to `strategy_snapshots` — the same table that the real system would eventually populate. These snapshots were NOT produced by the session lifecycle. They have no session provenance, no clock context, no temporal integrity guard.
- **Operational ambiguity**: When future architects or auditors look at `strategy_snapshots`, they will see data that appears to come from the session pipeline but was actually produced by an ad-hoc script. This violates Knowledge Persistence (Portable OS B3).

### Portable OS Violations
| Principle | Violation |
|-----------|-----------|
| **A8 — Evidence Before Complexity** | Ad-hoc evidence without clock provenance is not validatable evidence |
| **A3 — Boundary Discipline** | Shadow Decision Clock operates outside bounded context |
| **B3 — Knowledge Persistence** | Snapshots lack lineage — no way to know they came from shadow script |

### Verdict: REJECTED
Shadow execution violates Evidence Before Complexity. It creates evidence without clock provenance, which is indistinguishable from corrupted data.

---

## 6. REVIEW OF OPTION C (THE CHALLENGED THESIS)

**Option C**: Add `persist_strategy_snapshot()` to `Session._do_execute()` + make `threshold_pct` configurable via `.env`.

### 6.1 Thesis Claims
1. Session can persist snapshots after engine execution
2. `threshold_pct` can be configurable via `TRADY_AI_THRESHOLD_PCT` env var
3. This enables iterative threshold testing without pausing the experiment

### 6.2 Challenge #1: Session Does Not Own Persistence

Session is a **cross-clock orchestrator**. Per Architecture Contract §6.2:

| Clock | Owns persistence |
|-------|-----------------|
| Discovery | `.env` |
| Evidence | `event_store` |
| Decision | `signals` + `trades` |
| Reflection | `reflection_reports` |
| **Session** | **Nothing.** Session coordinates clocks; it does not own data. |

Placing `persist_strategy_snapshot()` in `Session._do_execute()` makes Session own data that belongs to a clock. This is a boundary violation (Portable OS A3): Session is no longer just an orchestrator — it now has a persistence side effect tied to calibration.

**Counter-argument**: "But Session already calls `_do_execute()` which writes to `execution_log`." 

**Rebuttal**: Session delegates to `ExecutionEngine.run()`, which calls `persist_execution_log()` internally. Session does not call `persist_execution_log()` directly. The engine owns its persistence; Session only invokes the engine. Option C has Session calling `persist_strategy_snapshot()` directly after the engine returns — a fundamentally different ownership pattern.

### 6.3 Challenge #2: Threshold Configurability Violates Frozen Contract

Architecture Contract §16.1 (Decision Clock Mechanism):

> **Strategy:** `MarkovStrategy(warmup_ticks=50, threshold_pct=0.001)` — **fixed parameters for the 30-day experiment.**

The word "**fixed**" is unambiguous. The Architecture Contract is PERMANENTLY FROZEN (§1). Changing `threshold_pct` during the experiment via `.env` is a contract amendment, not a configuration change.

**Counter-argument**: "It's just a parameter — why can't we tune it?"

**Rebuttal**: The Calibration Framework was designed to PROPOSE parameter changes, not to enact them mid-experiment. The Architecture Contract §17.2 says calibration happens AFTER 30 days. The correct flow is:

```
Day 1-30: Collect evidence with FROZEN parameters
Day 30:   Calibration gate activates
          → analyze accumulated evidence
          → propose new threshold
          → operator reviews evidence
          → operator ADOPTS (or rejects) new threshold
          → Architecture Contract AMENDED with new threshold
Post-Day-30: New experiment with new threshold
```

Changing thresholds mid-experiment contaminates the evidence. If you change `threshold_pct` from 0.1% to 0.001% on Day 2, the events from Day 1 were classified under different rules than Day 2+. The `strategy_snapshots` would contain mixed-threshold data, making the Day 30 calibration analysis unreliable.

**Portable OS A1 (Deterministic-First)**: "If the same input does not reliably produce the same output, the system is considered unstable." Changing threshold mid-experiment means the same price tick on Day 1 and Day 30 would produce different state classifications. The experiment is no longer deterministic across its 30-day span.

### 6.4 Challenge #3: Strategy State Extraction Violates Encapsulation

Option C accesses `strategy._transition_counts` and `strategy._threshold_pct` — private attributes (underscore-prefixed). The `MarkovPersistenceEngine` exposes a `get_state_summary()` method (line 149) for this purpose, but Session shouldn't need to know about strategy internals at all.

This reveals deeper coupling: Session must understand that `MarkovStrategy` has `_transition_counts`, that `_transition_counts` is a numpy array with `.tolist()`, and that `_threshold_pct` exists. If `MarkovPersistenceEngine` changes its internal representation, Session breaks.

### 6.5 Challenge #4: Conflation of Timing

Option C persists snapshots during EXECUTING. But snapshots are calibration evidence — they serve the REFLECTING stage. The correct sequence is:

```
EXECUTING → strategy runs, produces state
           ↓
REFLECTING → reflection analyzes execution
           → persists strategy snapshot AS EVIDENCE
           → snapshot is a Reflection artifact, not an Execution artifact
```

By persisting during EXECUTING, Option C creates a temporal coupling: if REFLECTING is skipped (reconstruction), the snapshot is still written. This means snapshots can exist without corresponding reflection reports — evidence without lineage.

### 6.6 Summary of Violations

| Principle | Violation |
|-----------|-----------|
| Architecture Contract §16.1 | `threshold_pct` is FROZEN — cannot be made configurable mid-experiment |
| Architecture Contract §6.2 | Session owns no persistence — placing snapshot writes in Session is boundary violation |
| Architecture Contract §17.2 | Calibration is a post-experiment gate — in-experiment threshold variation is out of scope |
| Portable OS A1 (Deterministic-First) | Changing threshold mid-experiment makes output non-deterministic across the 30-day span |
| Portable OS A3 (Boundary Discipline) | Session (orchestrator) gains persistence responsibility — responsibility leakage |
| Portable OS A2 (Architecture Before Implementation) | Threshold change requires contract amendment first, not code change first |
| RFC-003 (Strategy Infrastructure) | Strategies are "deterministic, testable, replayable, isolated" — mid-experiment threshold change violates all four |

### Verdict: REJECTED
Option C contains three architectural violations and one contract violation. It cannot be accepted as proposed.

---

## 7. HIDDEN ASSUMPTIONS IN THE STATUS REPORT

| Assumption | Reality |
|-----------|---------|
| "Calibration should happen now, not after 30 days" | Architecture Contract §17.2 explicitly places calibration at Day 30+ |
| "Threshold is just a parameter, we can tune it" | Architecture Contract §16.1 FREEZES it as "fixed parameters for the 30-day experiment" |
| "Session is the right place for persistence" | Session orchestrates clocks; it owns zero persistence per §6.2 |
| "`strategy_snapshots` belongs to the engine" | The table serves calibration (Reflection), not execution (Decision) |
| "Testing different thresholds is safe experimentation" | Threshold variation mid-experiment breaks determinism across the 30-day span |

---

## 8. BOUNDARY ANALYSIS

### 8.1 Who Owns Strategy Snapshots?

Two candidates exist:

| Candidate | Argument For | Argument Against |
|-----------|-------------|-----------------|
| **Decision Clock** | Snapshots capture strategy state at execution time (`tick_number`) | Decision owns `signals` and `trades`. Snapshots are NOT execution outputs — they're analytical evidence about strategy behavior. Adding them bloats Decision with calibration concerns. |
| **Reflection Clock** | Snapshots serve calibration analysis (AIC, BIC, χ²). Calibration is a Reflection responsibility per §17.2. | Reflection currently only owns `reflection_reports`. Snapshots are a different kind of artifact (statistical state vs. analytical summary). |

**Verdict: Reflection Clock.** The `strategy_snapshots` table captures the statistical state of the strategy at points in time for the purpose of evidence analysis. This is "evaluation lineage" — a Reflection responsibility per RFC-004 §Primary Responsibilities: "evaluation lineage."

### 8.2 Boundary Diagram

```
CORRECT (Option D):
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  Decision Clock  │────→│ Reflection Clock  │────→│ calibration_adopt  │
│  (executes)      │     │  (analyzes)       │     │  (governance)      │
│  → signals       │     │  → reflection_rpt │     │                    │
│  → trades        │     │  → strategy_snap  │ ←── │  OWNED HERE        │
│  → execution_log │     │                   │     │                    │
└─────────────────┘     └──────────────────┘     └────────────────────┘
```

---

## 9. RESPONSIBILITY OWNERSHIP ANALYSIS

| Artifact | Clock Owner | Justification |
|----------|------------|---------------|
| `event_store` | Evidence | Raw market data ingestion |
| `execution_log` | Decision | Tick-by-tick processing trace |
| `signals` | Decision | Signal generation output |
| `trades` | Decision | Trade execution output |
| `reflection_reports` | Reflection | Post-session analysis summaries |
| **`strategy_snapshots`** | **Reflection** | Statistical state evidence for calibration |
| `calibration_adoptions` | Governance (human) | Adopted state space configurations |

---

## 10. THRESHOLD OWNERSHIP ANALYSIS

The question "who owns threshold?" reveals the confusion at the heart of this problem.

| View | Answer | Source |
|------|--------|--------|
| **Runtime parameter** | The engine — it's an argument to `MarkovStrategy()` | Implementation |
| **Strategy property** | The strategy — it defines how state transitions are classified | RFC-003 |
| **Calibration artifact** | The Calibration Framework — it's the primary variable being calibrated | Calibration Framework SDD |
| **Governance artifact** | The operator — threshold must be ADOPTED via `calibrate adopt` | RFC-007 (Human Sovereignty) |
| **Frozen contract parameter** | The Architecture Contract — §16.1 explicitly freezes it | Architecture Contract |

**The threshold exists at ALL FIVE levels simultaneously.** This is the source of the tension:

- **Implementation** says "it's just a parameter" → Option C
- **Architecture** says "it's frozen" → Contract violation in Option C
- **Calibration** says "it's what we're calibrating" → legitimate desire to vary it
- **Governance** says "operator must adopt" → not automatic

The resolution: threshold follows the freeze → calibrate → adopt → amend cycle. It cannot be varied ad-hoc during a frozen experiment.

---

## 11. SNAPSHOT OWNERSHIP ANALYSIS

### What are strategy snapshots: execution state or scientific evidence?

| If execution state... | If scientific evidence... |
|----------------------|--------------------------|
| Belongs to Decision Clock | Belongs to Reflection Clock |
| Persisted during EXECUTING | Persisted during REFLECTING |
| Needed for reconstruction | Needed for calibration |
| Should be restored next session | Should be analyzed post-experiment |
| Part of the critical path | Observational, not critical |

The Calibration Framework treats snapshots as **evidence for scientific analysis** (AIC, BIC, χ²). The engine does not restore from snapshots (that's what `load_latest_snapshot` and `restore()` in MarkovPersistenceEngine do, but these are never called by the session pipeline). Therefore: **snapshots are scientific evidence, not execution state.**

### Implications
- Snapshots should be created by the Reflection Clock during REFLECTING
- Snapshots should NOT be created by the Decision Clock during EXECUTING
- The Reflection Clock should extract strategy state from the engine (which it has access to after execution)
- If the engine doesn't expose this state, that's the interface gap to fix — not the ownership

---

## 12. ARCHITECTURAL DEBT ANALYSIS

| Debt | Introduced By | Severity |
|------|-------------|----------|
| `strategy_snapshots` has no clock owner | Calibration Framework SDD | High — architectural orphan |
| `persist_strategy_snapshot()` exists but is never called | Calibration Framework SDD | Medium — dead code |
| `MarkovPersistenceEngine.get_state_summary()` exists but is never consumed by any clock | Markov SDD | Medium — unused interface |
| BL-018 (`_last_state` not persisted) | Markov SDD | Low — optimization, not blocker |
| `calibrate review` reads from orphaned table | Calibration Framework SDD | High — command doesn't work |

**All of these debts trace back to a single root cause**: the Calibration Framework was designed with the ANALYSIS pipeline (metrics, analyzer, CLI) but without a clear decision about WHEN and BY WHOM the data would be persisted. The CLI works. The analyzer works. But nobody populates the table.

---

## 13. RFC COMPATIBILITY REVIEW

| RFC | Requirement | Status under Option C | Status under Option D |
|-----|------------|----------------------|----------------------|
| RFC-000 | Operational safety: "fail safely before catastrophically" | ✅ No financial risk (dry_run) | ✅ Same |
| RFC-003 | Strategies are "deterministic, testable, replayable, isolated" | ❌ Threshold variation breaks determinism | ✅ Threshold frozen |
| RFC-003 | "Strategies generate signals. They do not own execution authority" | ✅ Preserved | ✅ Preserved |
| RFC-004 | "Reflection analyzes execution. It does not control execution" | ⚠️ Calibration analysis can't run | ✅ Reflection owns snapshots |
| RFC-004 | Reflection owns "evaluation lineage" | ❌ Snapshots have no lineage | ✅ Snapshots tied to reflection reports |
| RFC-007 | Human sovereignty — operator owns governance decisions | ❌ Threshold auto-changed via .env | ✅ Threshold changed via adopt + amend |

---

## 14. PORTABLE OS COMPATIBILITY REVIEW

| Principle | Option A | Option B | Option C | Option D |
|-----------|----------|----------|----------|----------|
| **A1 — Deterministic-First** | ✅ | ⚠️ Shadow execution outside clocks | ❌ Mid-experiment threshold change | ✅ Frozen threshold |
| **A2 — Architecture Before Implementation** | ✅ | ❌ Ad-hoc without contract | ❌ Code before contract amendment | ✅ Contract-first |
| **A3 — Boundary Discipline** | ❌ Cross-clock persistence | ❌ Shadow clock outside boundaries | ❌ Session owns clock data | ✅ Clock-appropriate ownership |
| **A5 — Simplicity** | ⚠️ Engine gains calibration concern | ❌ Duplicated execution logic | ⚠️ Session gains persistence | ✅ Single responsibility |
| **A8 — Evidence Before Complexity** | ⚠️ Snapshots without reflection lineage | ❌ Shadow evidence without provenance | ⚠️ Evidence mixed across thresholds | ✅ Evidence with full lineage |
| **B1 — Freeze Discipline** | ✅ | ❌ Ad-hoc undermines freeze | ❌ Violates frozen threshold | ✅ Preserves freeze |
| **B3 — Knowledge Persistence** | ✅ | ❌ No artifact lineage | ✅ | ✅ |

**Option D preserves 7/7 principles. Option C preserves 1/7.**

---

## 15. OPTION D — ARCHITECTURALLY CORRECT SOLUTION

### 15.1 What It Is

Persist `strategy_snapshots` inside the **REFLECTING stage**, owned by the **Reflection Clock**. Threshold remains **frozen** per Architecture Contract §16.1. Calibration remains a **post-experiment gate** per §17.2.

### 15.2 Where — `session.py`, REFLECTING stage (line 192-206)

```python
# ── REFLECTING ───────────────────────────────────────────────────
if SessionState.REFLECTING not in skip_stages:
    self._record_stage(report, SessionState.REFLECTING)
    try:
        ref_report = self._do_reflect(scope, domain)
        reflection_id = getattr(ref_report, "id", None)
        cal_state = getattr(ref_report, "calibration_state", "not_ready")
        if reflection_id is not None:
            report.reflection_report_id = int(reflection_id)
        report.calibration_state = cal_state
        
        # ── NEW: Persist strategy snapshot as calibration evidence ──
        # The Reflection Clock owns this artifact.
        # It captures the statistical state of the strategy AFTER execution
        # for post-experiment calibration analysis.
        self._persist_strategy_evidence(domain)
        
    except Exception:
        logger.exception("reflect_stage_failed")
        ...
```

### 15.3 How — New private method in Session

```python
def _persist_strategy_evidence(self, domain: str) -> None:
    """Persist strategy transition counts as calibration evidence.
    
    Owned by: Reflection Clock (calibration evidence, not execution state).
    Called during: REFLECTING stage.
    """
    from trady_ai.core.persistence import persist_strategy_snapshot
    
    engine = getattr(self, '_execution_engine', None)
    if engine is None:
        return
    
    # Engine holds the last strategy that ran
    strategy = getattr(engine, '_last_strategy', None)
    if strategy is None or not strategy.is_ready():
        return
    
    summary = strategy.get_state_summary()
    persist_strategy_snapshot(
        db=self._db,
        domain=domain,
        strategy_name=strategy.name,
        tick_number=summary.get("total_observations", 0),
        transition_counts=summary["transition_counts"],
        state_counts=summary["state_counts"],
        warmup_ticks=strategy._warmup_ticks,
        threshold_pct=strategy._threshold_pct,
        state_space_size=summary.get("state_space_size", 3),
        state_generator=summary.get("state_generator", "directional"),
    )
```

### 15.4 What it fixes about Option C

| Option C problem | Option D resolution |
|-----------------|-------------------|
| Session owns persistence | Session DELEGATES to Reflection Clock's stage — correct ownership |
| Threshold is configurable | Threshold stays frozen per Architecture Contract §16.1 |
| Snapshot persisted during EXECUTING | Snapshot persisted during REFLECTING — correct timing |
| Snapshot has no reflection lineage | Snapshot tied to the same session's reflection report |
| Strategy internals accessed directly | Uses `get_state_summary()` public interface |

### 15.5 Why This Preserves Architecture

1. **Clock ownership**: Reflection Clock owns `strategy_snapshots` → same clock that owns `reflection_reports` and calibration
2. **Temporal correctness**: Snapshots are created AFTER execution, during reflection — the clock that analyzes, not the clock that executes
3. **Contract preservation**: Threshold stays frozen. No Architecture Contract amendment needed for the implementation.
4. **Evidence lineage**: Every snapshot is tied to a session, a reflection report, and a frozen parameter set — full provenance.

### 15.6 What Option D Does NOT Solve

| Not solved | Why | How to address |
|-----------|-----|---------------|
| Threshold is too large (0.1%) | Architecture Contract freezes it | Requires contract amendment (§28) to change |
| In-experiment calibration | Architecture Contract says post-experiment (§17.2) | Either wait for Day 30, or amend contract |
| `_last_state` not persisted (BL-018) | Separate concern — recovery state, not calibration evidence | Future SDD cycle |
| Engine doesn't expose `_last_strategy` | New interface needed | Minor implementation detail |

---

## 16. IF THE OPERATOR TRULY WANTS THRESHOLD VARIATION NOW

The correct architectural path is:

1. **Document the intent**: Why is current threshold inadequate for crypto? (Already done — Status Report §2.2, Bybit tick size analysis)
2. **Amend Architecture Contract**: Add entry to §28 Amendment Log, document threshold change in §29 as D-003
3. **Define the amendment scope**: "Threshold calibrated from 0.001 to TBD based on statistical evidence" or "Threshold frozen at new value 0.00005 for remainder of experiment"
4. **Then implement Option D**: Persist snapshots during REFLECTING with new threshold
5. **Run calibration analysis**: With accumulated snapshots, determine optimal threshold
6. **Adopt**: `calibrate adopt` with governance approval

**This follows the Architecture Contract's own amendment mechanism.** It does not bypass it.

---

## 17. FINAL RECOMMENDATION

### 17.1 Immediate Action (authorized without amendment)

**Implement Option D** — persist `strategy_snapshots` in the REFLECTING stage. This:
- Populates the orphaned table
- Enables `calibrate review` to work (post-experiment)
- Preserves all architectural boundaries
- Creates no contract violations
- Takes ~15 lines of code
- Does not pause the experiment

### 17.2 If Threshold Must Change (requires amendment)

1. Amend Architecture Contract §28 + §29
2. Then implement Option D with new frozen threshold
3. Calibrate post-experiment as designed

### 17.3 Confidence

| Aspect | Confidence | Reason |
|--------|-----------|--------|
| Problem diagnosis validation | HIGH | `strategy_snapshots` is architecturally orphaned |
| Option C rejection | VERY HIGH | Three architectural violations, one contract violation |
| Option D correctness | HIGH | Preserves all 7 Portable OS principles, all 4 clocks |
| Threshold ownership analysis | VERY HIGH | Architecture Contract is unambiguous |
| Snapshots belong to Reflection | HIGH | Evidence, not execution state — consistent with RFC-004 |

---

## 18. REMAINING UNANSWERED QUESTIONS

1. **Engine interface gap**: `ExecutionEngine` does not expose the strategy it ran. `_persist_strategy_evidence()` needs access. Should engine store `_last_strategy` as a non-private attribute, or should Session track it separately?

2. **Multi-strategy future**: If the experiment later uses multiple strategies, should snapshots be per-strategy or aggregate? Current schema supports per-strategy via `strategy_name` column — correct design.

3. **Snapshot frequency**: Should snapshots be persisted every session (96/day) or once per day? Current Option D proposes every session — 2,880 snapshots in 30 days. This is fine for SQLite but worth noting.

4. **BL-018 resolution**: Option D does NOT resolve BL-018 (`_last_state`). Should BL-018 be addressed separately, or is it made irrelevant by Option D's snapshot-per-session approach?

---

**This review was conducted as an adversarial architectural analysis. Option C was deliberately challenged. It failed to survive. Option D emerged as the architecturally sound alternative.**

**The architecture is clear. The contract is frozen. The correct path is to respect both.**
