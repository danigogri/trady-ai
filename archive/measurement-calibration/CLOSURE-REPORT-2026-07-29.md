# DISCOVERY CLOSURE REPORT — Paper Trading Measurement Calibration

> **Date**: 2026-07-29 | **Status**: FINAL
> **Phase**: Discovery Closure | **Next Phase**: SDD Cycle (pending GO decision)
> **Artifacts Consolidated**: STATUS-REPORT + ARCHITECTURAL-REVIEW + RESEARCH-REPORT + DISCOVERY-REPORT

---

## 1. DISCOVERY SUMMARY

### 1.1 Evolution of Architectural Understanding

The discovery phase began with a practical observation: the Paper Trading experiment was running 55 sessions with zero trades and 99% NEUTRAL state classifications. Four investigations progressively deepened architectural understanding:

**Status Report** identified the symptoms: `strategy_snapshots` empty, threshold too large, no calibration adopted. It proposed three tactical options (A, B, C) focused on populating the orphaned table.

**Architectural Review** challenged those options through adversarial analysis. It identified that Option C violated the frozen Architecture Contract and that Session (a cross-clock orchestrator) should not own persistence. It proposed Option D: snapshots in the REFLECTING stage, owned by Reflection Clock. However, it accepted the frozen threshold as immutable, treating contract preservation as the highest architectural value.

**Research Report** introduced external evidence. It demonstrated that the frozen threshold was scientifically invalid for crypto tick data — a measurement validity problem, not a contract compliance problem. It identified ATR-based adaptive thresholds (Wilder, 1978) as a deterministic alternative and proposed a pilot→confirmatory two-phase experimental design supported by FDA adaptive trial methodology.

**Discovery Report** reframed the entire problem. It identified that the threshold is fundamentally a measurement instrument, not a strategy parameter. State classification (UP/DOWN/NEUTRAL) conceptually belongs to the Evidence Clock, not the Decision Clock. This single insight resolved ownership disputes across all previous reports and mapped every responsibility to an existing clock without architectural drift.

The maturation was: **symptoms → ownership → scientific validity → conceptual model**.

### 1.2 What Was Resolved

| Question | Resolution | Source |
|----------|-----------|--------|
| Why are there zero trades? | Threshold 0.1% produces 99% NEUTRAL states — measurement invalid for crypto | Status Report + Research Report |
| Who owns strategy_snapshots? | Reflection Clock | Architectural Review + Discovery Report |
| Is threshold a strategy parameter? | No — it's an Evidence Clock measurement calibration | Discovery Report |
| Do we need a new clock? | No — all responsibilities map to existing four clocks | Architectural Review + Discovery Report |
| Can we calibrate during the experiment? | Measurement calibration must happen BEFORE Day 0 (pre-experiment) | Research Report + Discovery Report |
| What measurement methodology? | ATR-based deterministic threshold with operator-adopted α | Research Report |

---

## 2. VALIDATED ARCHITECTURAL DECISIONS

### 2.1 Decisions Validated Across Multiple Reports

| # | Decision | Evidence | Origin | Confidence |
|---|----------|----------|--------|-----------|
| **D1** | `strategy_snapshots` belongs to the Reflection Clock | RFC-004: Reflection owns "evaluation lineage" and "calibration assessments." The snapshot captures statistical behavior of classified measurements — this is analysis, not execution. | Architectural Review + Discovery Report | **VERY HIGH** |
| **D2** | State classification (UP/DOWN/NEUTRAL) is an Evidence Clock measurement responsibility | Architecture Contract §6.1: Evidence Clock "ingests real-time market data." Classification is the final step of ingestion — converting raw ticks into semantically meaningful states. | Discovery Report | **HIGH** |
| **D3** | Threshold is a measurement instrument calibration, not a strategy parameter | Changing threshold changes the semantic meaning of states (what "UP" means), not how the model processes states. A thermometer calibrated in Celsius vs Fahrenheit is the analog — same underlying physics, different measurement units. | Discovery Report + Research Report | **HIGH** |
| **D4** | No fifth clock is needed | Architecture Contract §6.3 already evaluated and rejected Calibration Clock as "a mode of Reflection at extended frequency." Measurement calibration is a Governance activity (pre-experiment). Calibration analysis is Reflection (post-execution). Both map to existing clocks. | Architectural Review + Discovery Report | **VERY HIGH** |
| **D5** | Strategy Snapshots are a single unified artifact serving multiple consumers | A DTMC's transition matrix simultaneously defines the model (execution), serves as evidence for quality (calibration), and enables reconstruction (recovery). Splitting into three artifacts creates three copies of the same mathematical object — violates Portable OS A5. ML frameworks (PyTorch, TensorFlow) save unified checkpoints. | Research Report + Discovery Report | **HIGH** |
| **D6** | Measurement calibration must precede the confirmatory experiment | Standard scientific methodology: validate measurement instrument before data collection. The experiment tests the hypothesis ("can Markov detect patterns in crypto?"), not the measurement ("what threshold works?"). | Research Report + Discovery Report | **HIGH** |
| **D7** | Session does not own persistence | Architecture Contract §6.2: each clock owns its persistence. Session orchestrates clocks; it owns no data. Placing snapshot writes in Session is a boundary violation. | Architectural Review | **VERY HIGH** |

### 2.2 Decisions Validated by Single Report (Not Contradicted)

| # | Decision | Evidence | Origin | Confidence |
|---|----------|----------|--------|-----------|
| **D8** | ATR-based threshold is deterministic and appropriate for crypto | Wilder (1978): ATR formula is mathematically deterministic — same price history → same threshold. Adapts to volatility regimes without AI/ML. Widely used in industry for position sizing and stop-loss placement. | Research Report | **HIGH** |
| **D9** | `_compute_day()` fix (calendar day counter) is correct and validated | Commit 52d0c71: DAY_ZERO frozen, session counter per day. 55 sessions confirmed correct behavior. Architecture Contract §16.1 day semantics preserved. | Status Report | **VERY HIGH** |
| **D10** | EventCapture fix (market_input fields) is correct and validated | Commit 6ba3b08: domain-agnostic dedup using MarketInput, not raw event. VPS sync confirmed. | Status Report | **VERY HIGH** |

---

## 3. REJECTED ALTERNATIVES

| # | Alternative | Rejection Reason | Source |
|---|------------|-----------------|--------|
| **R1** | Option A: `persist_strategy_snapshot()` inside `ExecutionEngine.run()` | Cross-clock coupling: Decision Clock persists calibration evidence for Reflection Clock. Engine does not receive `domain` parameter. Violates Portable OS A3 (Boundary Discipline). | Architectural Review |
| **R2** | Option B: Shadow calibration script (parallel execution) | Duplicated execution logic outside clock system. Evidence without clock provenance — indistinguishable from corrupted data. Violates Portable OS A8 (Evidence Before Complexity) and B3 (Knowledge Persistence). | Architectural Review |
| **R3** | Option C: Session-level snapshot persistence + configurable threshold | Three architectural violations: (1) Session owns persistence (boundary violation), (2) threshold configurability violates Architecture Contract §16.1 frozen parameters, (3) threshold change mid-experiment breaks determinism across 30-day span. Violates Portable OS A1, A2, A3. | Architectural Review |
| **R4** | B+C hybrid (dual-source threshold: DB + config) | Over-engineering. Two mechanisms for one value increases operational surface without proportional benefit. Violates Portable OS A5 (Simplicity), A6 (Governance Minimalism), B5 (Operational Progress). | Status Report |
| **R5** | Additional clock (Calibration Clock, Measurement Clock) | Architecture Contract §6.3 already rejected Calibration Clock. Measurement calibration is Governance, not a recurring process. Adding a clock for a pre-experiment activity introduces lifecycle complexity without runtime value. | Architectural Review + Discovery Report |
| **R6** | Splitting strategy_snapshots into runtime/calibration/recovery artifacts | Three copies of the same N×N transition matrix stored at potentially different tick_numbers with different provenance. Reconciliation burden, storage waste, provenance confusion. Violates Portable OS A5. ML industry practice uses unified checkpoints. | Research Report + Discovery Report |
| **R7** | Threshold as a Decision Clock strategy parameter (current implementation) | Conceptual error. Threshold controls measurement (state classification), not strategy (transition learning). MarketStateTracker running inside ExecutionEngine is a hidden responsibility leakage from Evidence Clock to Decision Clock. | Discovery Report |
| **R8** | Embedded pilot phase (2-day pilot within 30-day experiment) | Measurement calibration during the experiment contaminates evidence. Pilot data and confirmatory data use different measurement instruments — incommensurable states. Pre-Day-0 calibration is stronger science. | Discovery Report |

---

## 4. SCIENTIFIC CONCLUSIONS

### 4.1 Conclusions Supported by Scientific Literature

| # | Conclusion | Literature Basis |
|---|-----------|-----------------|
| **S1** | Frozen measurement instrument applied to wrong domain produces invalid evidence | Campbell & Stanley (1963): internal validity requires measurement instrument appropriate for phenomenon. Bybit tickSize data confirms 870-tick gap between threshold and reality. |
| **S2** | Pre-specified adaptive designs preserve scientific validity | FDA Adaptive Design Guidance (2019): adaptations allowed when rules are pre-specified, Type I error controlled, and independent review exists. Our analog: AIC/BIC/χ² comparison, dry_run mode, operator governance. |
| **S3** | ATR-based threshold is a deterministic volatility-adaptive measurement | Wilder (1978): ATR formula is mathematically deterministic. Used in position sizing and stop-loss placement across futures, forex, and equities. |
| **S4** | Market efficiency is not stationary — adaptive measurement is theoretically justified | Adaptive Market Hypothesis (Lo, 2004): degree of efficiency varies with market ecology. Khuntia & Pattanayak (2018): Bitcoin exhibits evolving efficiency — dynamic dependence changes over time. |
| **S5** | Markov chain persistence standard: transition matrix + hyperparameters | hmmlearn, pomegranate, ghmm: industry standard serialization includes transition matrix (A), emission probabilities (B), initial distribution (π), training iterations, model hyperparameters. Trady AI already captures transition matrix, state counts, tick_number, and config — missing π (initial distribution). |

### 4.2 Conclusions from Architectural Reasoning (Not External Literature)

| # | Conclusion | Basis |
|---|-----------|-------|
| **S6** | Strategy Snapshots have six simultaneous identities: execution state, serialized strategy state, scientific evidence, calibration artifact, recovery artifact, statistical checkpoint | DTMC formal definition: transition matrix fully characterizes the chain. ML industry practice: unified checkpoints. Architectural analysis: all six interpretations are true simultaneously — this is the mathematical nature of a Markov chain. |
| **S7** | Measurement instrument calibration is distinct from model calibration | Conceptual distinction: calibrating a thermometer (instrument) vs calibrating a weather prediction model. Both use "calibration" but operate at different architectural layers. Evidence Clock owns the instrument; Decision Clock owns the model. |
| **S8** | Incommensurability across thresholds is an architectural concern, not a procedural one | States classified at 0.1% are semantically incommensurable with states classified at 0.001%. "UP at 0.1%" ≠ "UP at 0.001%". The architecture must prevent mixing incommensurable states — the current "freeze" approach is procedural mitigation, not architectural prevention. |

---

## 5. GOVERNANCE BASELINE

### 5.1 Frozen Governance Principles

These principles must remain immutable throughout the SDD cycle. The SDD may implement mechanisms that realize these principles but may not challenge the principles themselves.

| # | Principle | Source | Scope |
|---|----------|--------|-------|
| **G1** | **Deterministic measurement**: State classification must produce identical output for identical input. ATR-based threshold achieves this — fixed formula, deterministic output. | Portable OS A1 | Evidence Clock |
| **G2** | **Operator sovereignty**: The operator adopts the measurement methodology (α constant for ATR), the state space configuration (states, generator), and any parameter changes. No automatic adoption without governance. | RFC-007 | All clocks |
| **G3** | **Evidence-based adoption**: Every governance decision (adopt threshold methodology, adopt state space) must be supported by verifiable evidence (AIC, BIC, χ², persistence, entropy). `calibrate review` is the evidence mechanism; `calibrate adopt --confirm` is the governance mechanism. | Portable OS A8 | Governance |
| **G4** | **Frozen experiment**: Once the confirmatory experiment begins (Day 0 with validated measurement instrument), the measurement methodology is frozen for the experiment duration. Architecture Contract §16.1 applies to the confirmatory phase. | Architecture Contract + Portable OS B1 | Experiment lifecycle |
| **G5** | **Clock boundary integrity**: No clock may assume responsibilities of another clock. Evidence measures. Decision decides. Reflection analyzes. Governance adopts. Session orchestrates. | Architecture Contract §6.2 | All clocks |
| **G6** | **Reproducibility**: Every artifact (snapshot, adoption, bundle) must contain sufficient provenance for future operators to reproduce the analysis. This includes: threshold methodology, α constant, state space configuration, domain, date range. | Portable OS B3 | All artifacts |
| **G7** | **Contract amendment governance**: Any change to frozen parameters requires Architecture Contract amendment (§28) with documented deviation (§29). The amendment process is: evidence → operator review → adoption → contract amendment. | Architecture Contract §27-29 | Governance |

---

## 6. DISCOVERY CONSTRAINTS

The following topics are considered CLOSED by this discovery phase. The SDD cycle should not reopen these discussions without compelling new evidence that contradicts the findings below.

| # | Constraint | Rationale |
|---|-----------|-----------|
| **C1** | **No new clocks.** The four-clock architecture (Discovery, Evidence, Decision, Reflection) is sufficient. Calibration is Reflection. Measurement is Evidence. Governance is operator. | Architecture Contract §6.3 already evaluated and rejected additional clocks. Discovery Report confirmed all responsibilities map to existing clocks. |
| **C2** | **No additional state spaces.** Three states (UP/DOWN/NEUTRAL) are fixed for this experiment. The operator's explicit instruction: "tres estados está bien." Research Report confirmed: more states don't add value for crypto tick data at this granularity. | Operator decision + Research Report |
| **C3** | **No AI/ML for threshold.** Threshold methodology must be deterministic. ATR-based computation satisfies this. Neural networks, reinforcement learning, or any non-deterministic threshold adaptation is prohibited. | RFC-005: intelligence assists, does not own operations. Portable OS A1: deterministic-first. |
| **C4** | **No mid-experiment threshold changes during confirmatory phase.** The confirmatory experiment (post-Day-0) uses a frozen measurement methodology. Changing the measurement instrument mid-experiment produces incommensurable states. | Governance baseline G4 + scientific conclusion S8 |
| **C5** | **Snapshot is a single unified artifact.** No splitting into runtime/calibration/recovery variants. Multiple consumers, one table. The SDD may add a `purpose` or `created_by` column for provenance without splitting. | Rejected alternative R6 + Portable OS A5 |
| **C6** | **Session does not own persistence.** Session orchestrates clocks. It delegates to clock-specific methods. It must not directly call `persist_*` functions that belong to clocks. | Validated decision D7 + Architecture Contract §6.2 |
| **C7** | **Threshold belongs to Evidence Clock conceptually.** The SDD may phase implementation (transitional design) but the conceptual ownership is resolved. State classification = measurement = Evidence Clock. | Validated decision D2 |

---

## 7. OPEN DESIGN QUESTIONS

The following questions are appropriate for the SDD cycle. They are design questions, not conceptual questions — the SDD will determine HOW to implement validated architectural decisions, not WHETHER to implement them.

### 7.1 Measurement Calibration (Evidence Clock)

| # | Question | Type |
|---|---------|------|
| **Q1** | What is the optimal ATR lookback period (N) for crypto tick data? Wilder recommends 14 for daily bars. Sub-second ticks require empirical determination. | Design parameter |
| **Q2** | What α multiplier (governance constant) produces the best state distribution? Must be determined through pre-Day-0 calibration using sample Bybit testnet data. | Calibration parameter |
| **Q3** | How should classified states be persisted? Options: new `market_states` table, additional columns in `event_store`, or derived on-the-fly. Tradeoff: storage vs computation vs query simplicity. | Persistence design |
| **Q4** | How should ATR be computed from tick-level data? ATR requires high, low, close. Tick data has individual trade prices. Needs aggregation window (1-second? 5-second?) to produce OHLC bars for ATR calculation. | Algorithm design |

### 7.2 Snapshot Persistence (Reflection Clock)

| # | Question | Type |
|---|---------|------|
| **Q5** | How does ReflectionEngine access the strategy's transition matrix after execution? Current engine does not expose `_last_strategy`. Options: add public attribute, add `get_last_strategy()` method, have Session pass strategy reference to Reflection. | Interface design |
| **Q6** | Should snapshots be persisted every session (96/day) or at reduced frequency (once per day, once per N sessions)? Every session provides maximum evidence density. 96 × 30 = 2,880 snapshots — acceptable for SQLite (N×N matrix is tiny). | Frequency design |
| **Q7** | Should the `strategy_snapshots` schema be amended to include `created_by` column for provenance? Currently has `domain`, `strategy_name`, `tick_number` — no indication of which clock created it. Adding `created_by = "reflection_engine"` provides audit trail. | Schema design |

### 7.3 Transitional Design

| # | Question | Type |
|---|---------|------|
| **Q8** | How to migrate from current implementation (MarketStateTracker in Decision Clock) to target architecture (state classification in Evidence Clock) without breaking the running experiment? Options: parallel tracks (old code continues, new code developed separately), incremental migration (Evidence Clock adds classification, Decision Clock gradually stops doing it), or clean break (SDD implements target directly). | Migration design |
| **Q9** | Should ATR computation be implemented as a new StateGenerator (e.g., `ATRStateGenerator`) or as a modification to `MarketStateTracker`? The StateGenerator ABC already exists. ATR threshold could be a generator parameter — clean interface fit. | Interface design |

### 7.4 Contracts and Compatibility

| # | Question | Type |
|---|---------|------|
| **Q10** | What Architecture Contract amendments are required? Minimum: §28 Amendment Log entry documenting threshold methodology change from fixed 0.1% to ATR-based. §29 Documented Deviation for crypto domain measurement recalibration. | Contract design |
| **Q11** | Are existing tests compatible with ATR-based threshold? Tests that assert specific `threshold_pct` values or specific state classification behavior will need updating. Impact assessment needed. | Compatibility design |
| **Q12** | How does `calibrate review` handle snapshots produced with ATR-based threshold vs fixed threshold? The threshold methodology is part of the snapshot (`threshold_pct` column). Analyzer must handle variable thresholds correctly — currently it reads `threshold_pct` from snapshot, which would naturally contain the ATR-computed value. | Compatibility design |

---

## 8. SDD ENTRY CRITERIA

### 8.1 Criteria

| # | Criterion | Status | Evidence |
|---|----------|--------|----------|
| **E1** | Conceptual ownership of all artifacts resolved | ✅ MET | Discovery Report §6.1 maps every responsibility to a clock |
| **E2** | Measurement methodology selected | ✅ MET | ATR-based deterministic threshold with operator-adopted α |
| **E3** | Rejected alternatives documented with rationale | ✅ MET | This report §3: 8 rejected alternatives with Portable OS justification |
| **E4** | Governance baseline frozen | ✅ MET | This report §5: 7 governance principles immutable for SDD |
| **E5** | Discovery constraints defined | ✅ MET | This report §6: 7 topics closed to further discovery |
| **E6** | Open design questions scoped | ✅ MET | This report §7: 12 design questions appropriate for SDD |
| **E7** | No remaining conceptual ambiguity | ✅ MET | All four reports converged on consistent model. No contradictions remain between reports. |
| **E8** | Architecture Contract amendment path identified | ✅ MET | §28 Amendment Log, §29 Documented Deviations. Minimum 2 entries needed. |

### 8.2 Assessment

All eight entry criteria are met. The discovery phase has achieved conceptual closure. Remaining open questions are design questions (HOW to implement), not conceptual questions (WHAT to implement or WHY). This is the definition of SDD readiness.

---

## 9. DISCOVERY CLOSURE DECISION

### RECOMMENDATION: GO WITH CONDITIONS

**The Discovery Phase has achieved sufficient conceptual maturity to authorize the SDD Cycle.**

The following conditions must be satisfied before or during the SDD cycle:

| # | Condition | Rationale |
|---|----------|-----------|
| **1** | **Architecture Contract amendment** before any code change: document threshold methodology change from fixed 0.1% to ATR-based in §28 Amendment Log, document crypto domain measurement recalibration as D-003 in §29 Documented Deviations | Governance baseline G7: contract amendment governance. Portable OS A2: Architecture Before Implementation. |
| **2** | **Pre-Day-0 measurement calibration**: before the confirmatory experiment begins, collect sample Bybit testnet data and determine optimal ATR period (N) and α constant through AIC/BIC/χ² comparison. Operator adopts via `calibrate adopt --confirm`. | Scientific conclusion S1: measurement validity before data collection. Governance baseline G3: evidence-based adoption. |
| **3** | **Option D as implementation baseline**: persist `strategy_snapshots` in REFLECTING stage, owned by Reflection Clock. Session delegates to Reflection, not directly persists. | Validated decision D1 + D7. Rejected alternative R3. |
| **4** | **Single unified snapshot artifact**: add `created_by` column for provenance. Do not split into multiple tables. | Validated decision D5. Rejected alternative R6. Discovery constraint C5. |
| **5** | **No mid-experiment threshold changes**: confirmatory phase uses frozen measurement methodology. Architecture Contract §16.1 applies to confirmatory phase with adopted ATR-based threshold. | Governance baseline G4. Scientific conclusion S8. |
| **6** | **SDD scope limited to design questions**: the SDD should focus on Q1-Q12 (this report §7). It should not reopen discovery constraints (this report §6). It should not challenge governance baseline (this report §5). | Discovery constraint C1-C7. |

### Confidence: VERY HIGH

The discovery phase produced four complementary investigations, each validating and refining the previous. The conceptual model is now internally consistent, externally validated (scientific literature, industry practice), and architecturally sound (Portable OS, Architecture Contract, RFC ecosystem). No contradictions remain. No gaps persist. Twelve design questions are appropriately scoped for SDD resolution.

---

## 10. ARTIFACT INDEX

| # | Document | Purpose | Path |
|---|----------|---------|------|
| 1 | Status Report | Symptoms, current state, three options | `paper_trading/STATUS-REPORT-2026-07-29.md` |
| 2 | Architectural Review | Adversarial analysis, Option D proposal | `paper_trading/ARCHITECTURAL-REVIEW-2026-07-29.md` |
| 3 | Research Report | Scientific evidence, ATR methodology, pilot design | `paper_trading/RESEARCH-REPORT-2026-07-29.md` |
| 4 | Discovery Report | Conceptual reframe: threshold = measurement | `paper_trading/DISCOVERY-REPORT-2026-07-29.md` |
| **5** | **Closure Report** | **Consolidated baseline for SDD** | **`paper_trading/CLOSURE-REPORT-2026-07-29.md`** |

---

**Discovery Phase: CLOSED. SDD Cycle: AUTHORIZED with conditions.**
