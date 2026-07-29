# ARCHITECTURAL DISCOVERY REPORT — Second Stage

> **Date**: 2026-07-29 | **Type**: Conceptual Discovery
> **Status**: Provisional — open to falsification
> **Artifacts Synthesized**: Status Report + Architectural Review + Research Report

---

## 0. EXECUTIVE SUMMARY

### 0.1 The Discovery

**The threshold is a measurement instrument, not a strategy parameter.**

Three previous investigations (Status Report, Architectural Review, Research Report) debated WHO should own the threshold and WHEN it should change. None questioned WHAT the threshold actually is.

A price tick of $87,234.50 is a measurement. Classifying it as UP, DOWN, or NEUTRAL is a measurement. The 0.1% parameter that controls this classification is the calibration of a measurement instrument.

This reframes the entire architectural problem:

| Previous framing | New framing |
|-----------------|-------------|
| "Threshold is a MarkovStrategy parameter" | Threshold is an Evidence Clock measurement calibration |
| "Decision Clock owns the threshold" | Evidence Clock classifies states; Decision Clock consumes them |
| "Strategy snapshots capture engine state" | Snapshots capture the statistical behavior of classified measurements |
| "Calibrate threshold = tune strategy" | Calibrate threshold = calibrate measurement instrument |

### 0.2 What Changes

The existing four-clock architecture **already accommodates this reframing**. No new clocks are needed. The conceptual adjustment is:

1. State classification (UP/DOWN/NEUTRAL) migrates conceptually from Decision Clock to Evidence Clock
2. The threshold becomes an Evidence Clock governance parameter — like frozen eligibility rules for market selection
3. Strategy snapshots become Reflection artifacts that analyze Evidence Clock's classified measurements
4. Calibration becomes measurement instrument calibration — a pre-experiment activity, not a post-experiment gate

### 0.3 What Does NOT Change

- Four-clock architecture ✅ preserved
- Clock boundaries ✅ preserved (actually strengthened)
- Unidirectional dependencies ✅ preserved
- RFC ownership ✅ preserved
- Portable OS compliance ✅ preserved

---

## 1. MEASUREMENT INSTRUMENT

### 1.1 Four Interpretations of Threshold Calibration

| Interpretation | What it means | Who owns it | When it happens |
|---------------|---------------|-------------|-----------------|
| **Model calibration** | Tuning a strategy hyperparameter (like warmup_ticks) | Strategy/Decision Clock | During experiment, via evidence |
| **Measurement calibration** | Calibrating the instrument that converts raw data into classified observations | Evidence Clock | Before experiment, validated once |
| **Experiment configuration** | Setting up the experimental apparatus | Governance/Operator | Before Day 0, frozen thereafter |
| **Domain adaptation** | Adjusting the system to a new market domain | Governance + Evidence | Once per domain, at domain onboarding |

### 1.2 Analysis

**Model calibration** is the current implementation's view. It's also the source of the confusion. Model calibration (tuning hyperparameters based on training data) is what ML practitioners do. But threshold_pct is not a hyperparameter — it doesn't control model complexity or regularization. It controls the **semantic meaning** of the input data. Changing threshold_pct changes what "UP" means, not how the model processes "UP."

**Measurement calibration** is the scientifically correct view. A thermometer calibrated in Celsius measures temperature differently than one calibrated in Fahrenheit. Both are valid instruments, but their readings are incommensurable. Similarly, state classification at 0.1% threshold produces incommensurable states compared to 0.001% threshold. The Markov engine sees "UP" in both cases — but "UP" means different things.

**Experiment configuration** is how the Architecture Contract currently treats it (§16.1: "fixed parameters for the 30-day experiment"). This is correct as a governance stance but incomplete as a conceptual model. It says "thou shalt not change" without explaining why.

**Domain adaptation** is the operational reality. The threshold was frozen for Polymarket football. When the domain changed to BYBIT-SPOT (§30), the threshold should have been re-calibrated for the new domain's measurement characteristics (tick size, volatility profile, resolution window). This was the gap.

### 1.3 Recommendation

**Threshold = Measurement Instrument Calibration**. It belongs to the Evidence Clock's measurement apparatus. It should be calibrated ONCE per domain (during domain onboarding), validated with empirical evidence (pilot data), and frozen thereafter. This is conceptually identical to how the Evidence Clock already handles market eligibility rules: frozen rules, operator-adopted, domain-specific.

---

## 2. PILOT PHASE

### 2.1 Is a Pilot Phase Stronger Science?

The question is not "should we have a pilot?" — it's "when does measurement calibration happen?"

| Model | Measurement calibration | Confirmatory experiment |
|-------|------------------------|------------------------|
| **Current (no pilot)** | Assumed correct from Polymarket → carried to crypto | 30 days with unvalidated instrument |
| **Research Report (2+28)** | 2-day pilot discovers threshold | 28-day confirmatory with validated instrument |
| **Discovery (this report)** | Domain onboarding calibrates instrument ONCE | 30-day experiment with pre-validated measurement |

### 2.2 The Stronger Model

The pre-validated measurement model (this report) is scientifically strongest because:

1. **Measurement validity is established BEFORE data collection begins.** This is standard practice in every empirical science. You don't build a telescope during the observation campaign.

2. **The experiment tests the HYPOTHESIS** ("can Markov detect patterns in crypto?"), not the MEASUREMENT ("what threshold produces valid states?"). Confounding the two contaminates the experiment.

3. **Reproducibility**: A future operator replicating this experiment needs to know (a) the measurement instrument calibration used, and (b) that it was validated BEFORE data collection. A pilot phase embedded in the experiment timeline conflates (a) and (b).

4. **Governance**: The operator adopts the measurement calibration as a frozen governance decision. The experiment then validates the strategy under that calibration. This is a clean separation of concerns.

### 2.3 Recommendation

**Domain Onboarding Calibration** — a pre-Day-0 activity that:
1. Collects representative sample data from the target domain (e.g., 4 hours of Bybit testnet ticks)
2. Runs calibration analysis (AIC, BIC, χ²) across candidate thresholds
3. Operator reviews evidence and adopts a threshold
4. Threshold is frozen as an Evidence Clock governance parameter
5. Day 0 begins with validated measurement instrument

This is distinct from the Research Report's "pilot → confirmatory" design. In that design, the pilot IS part of the experiment. In this design, calibration is a pre-experiment activity — like calibrating a microscope before looking through it.

---

## 3. THRESHOLD LIFECYCLE

### 3.1 Four Lifecycle Models

Assuming 3 Markov states (UP/DOWN/NEUTRAL) are fixed:

| Model | When threshold changes | Governance | Example |
|-------|----------------------|-----------|---------|
| **Fixed forever** | Never | Frozen in Architecture Contract | Current §16.1 |
| **Fixed per experiment** | Between experiments (30-day campaigns) | Operator adopts before each experiment | Research Report recommendation |
| **Deterministic per market** | Automatically, based on market data (volatility) | Operator adopts α constant (governance parameter) | ATR-based threshold |
| **Deterministically recomputed** | At review windows (every 7 days) | Operator reviews evidence, may adopt new threshold | Calibration as continuous process |

### 3.2 Analysis

**Fixed forever** assumes market measurement characteristics never change. For crypto, this is demonstrably false: BTC volatility ranges from 0.5% to 10% daily. A fixed threshold calibrated during a calm period fails during a volatile period, and vice versa.

**Fixed per experiment** is the standard scientific model: one experiment, one measurement instrument. Clean evidence. But it requires manual re-calibration between experiments — operational burden.

**Deterministic per market** adapts automatically to market conditions while remaining deterministic. An ATR-based threshold widens during high volatility and narrows during low volatility. The governance parameter is α (the multiplier), not the threshold itself. This is the "teach a man to fish" model.

**Deterministically recomputed** at review windows introduces periodic threshold changes within an experiment. This contaminates evidence across review periods — states classified in Week 1 are incommensurable with states classified in Week 2.

### 3.3 Recommendation

**Deterministic per market with operator-adopted α**. This provides:
- ✅ Deterministic measurement (Portable OS A1) — same price history → same threshold
- ✅ Automatic adaptation to volatility regimes — no manual recalibration
- ✅ Single governance parameter (α) — operator adopts once, Evidence Clock applies
- ✅ Clean evidence across the full experiment — same measurement methodology throughout
- ✅ Stronger science than fixed threshold — measurement adapts to the phenomenon being measured

The ATR-based formula:

```
threshold_pct(t) = α × ATR_N(t) / price(t)
```

Where:
- ATR_N(t) = N-period Average True Range (Wilder, 1978)
- price(t) = current market price
- α = governance constant (e.g., 0.5 means threshold = 50% of normalized ATR)

For BTC at $87,000 with 14-period ATR of $150: threshold = 0.5 × 150/87000 = 0.00086% ≈ 0.001%. For BTC in high volatility (ATR = $1,500): threshold = 0.5 × 1500/87000 = 0.0086% ≈ 0.01%. The threshold automatically widens when the market is volatile and narrows when calm.

---

## 4. EVIDENCE RESPONSIBILITIES

### 4.1 The Hidden Responsibility

The Architecture Contract §6.1 says the Evidence Clock "ingests real-time market data" and persists to event_store. But currently, state classification (raw price → UP/DOWN/NEUTRAL) happens inside the Decision Clock via MarketStateTracker.

This is a **hidden responsibility leakage**. The Decision Clock is performing measurement (classification) when it should only be performing decision (strategy evaluation). The Evidence Clock should own measurement from end to end: raw tick → MarketInput → MarketState (classified).

### 4.2 Responsibility Distribution

| Activity | Current Owner | Correct Owner | Justification |
|----------|--------------|---------------|---------------|
| Capture raw tick | Evidence Clock | Evidence Clock | ✅ Already correct |
| Persist raw event | Evidence Clock | Evidence Clock | ✅ Already correct |
| **Classify state (UP/DOWN/NEUTRAL)** | **Decision Clock** (MarketStateTracker) | **Evidence Clock** | Measurement, not decision |
| Persist classified state | Not persisted separately | Evidence Clock | Enables calibration without re-running engine |
| Learn transitions | Decision Clock (MarkovStrategy) | Decision Clock | ✅ Already correct |
| Generate signals | Decision Clock | Decision Clock | ✅ Already correct |
| Execute trades | Decision Clock | Decision Clock | ✅ Already correct |
| Create snapshot | Not done | Reflection Clock | Analysis of Evidence Clock's measurements |
| Persist snapshot | Not done | Reflection Clock | Evaluation lineage |
| Analyze snapshot (AIC, BIC, χ²) | CalibrationAnalyzer | Reflection Clock | ✅ Already correct |

### 4.3 Can Evidence Produce a Snapshot that Reflection Later Analyzes?

**No — and this distinction is critical.** The Evidence Clock produces classified states (measurements). The Reflection Clock produces snapshots (analysis of those measurements). They are different artifacts created by different clocks.

```
Evidence Clock:           Reflection Clock:
  raw tick                    reads classified states
    ↓                              ↓
  classify (UP/DOWN/NEUTRAL)    computes transition matrix
    ↓                              ↓
  persist classified state      persist snapshot (analysis)
    ↓                              ↓
  (done)                       CalibrationAnalyzer consumes snapshot
```

This separation is architecturally cleaner than the current model (where Decision does both classification AND analysis). The Evidence Clock measures. The Reflection Clock analyzes measurements. Neither performs the other's responsibility.

### 4.4 What This Means for Snapshots

A Strategy Snapshot is an **analysis artifact** that captures the statistical behavior of classified measurements. It is NOT a measurement itself. It is NOT execution state. It is:

> "Given these N classified states produced by the Evidence Clock using threshold α × ATR/price, here is the observed transition matrix, here are the information criteria, and here is the model quality."

This belongs unequivocally to the Reflection Clock. The Reflection Clock's lifecycle already includes "analyze outcomes" and "calibration assessments." A snapshot is the primary evidence for calibration assessment.

---

## 5. STRATEGY SNAPSHOT LIFECYCLE

### 5.1 Complete Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    SNAPSHOT LIFECYCLE                           │
│                                                                 │
│  BIRTH                                                          │
│  ├── When: During REFLECTING stage, after execution completes   │
│  ├── Who creates: ReflectionEngine.reflect()                    │
│  ├── From what: MarkovPersistenceEngine.get_state_summary()     │
│  └── Precondition: strategy.is_ready() == True                  │
│                                                                 │
│  PERSISTENCE                                                    │
│  ├── Who persists: Reflection Clock → strategy_snapshots table  │
│  ├── What is stored: transition_counts, state_counts,           │
│  │   threshold_pct, warmup_ticks, state_space_size,             │
│  │   state_generator, tick_number, snapshot_at                  │
│  ├── Association: Linked to reflection_report via session       │
│  └── Idempotency: INSERT OR REPLACE on (domain, tick_number)    │
│                                                                 │
│  RESTORATION (for Decision Clock recovery)                      │
│  ├── When: Session reconstruction detects interrupted execution │
│  ├── Who restores: ExecutionEngine via load_latest_snapshot()   │
│  ├── What is restored: transition_counts → _transition_counts   │
│  └── Ownership note: Decision CONSUMES snapshot for recovery,   │
│      but does not CREATE it                                     │
│                                                                 │
│  ANALYSIS (for calibration)                                     │
│  ├── When: calibrate review command (operator-initiated)        │
│  ├── Who analyzes: CalibrationAnalyzer.analyze()                │
│  ├── What is computed: AIC, BIC, Markov χ², persistence,        │
│  │   conditional entropy                                        │
│  └── Output: EvidenceReport (displayed to operator)             │
│                                                                 │
│  CONSUMPTION (governance)                                       │
│  ├── When: calibrate adopt command (operator-initiated)         │
│  ├── Who consumes: Operator (human governance)                  │
│  ├── What is adopted: state_space_size, state_generator,        │
│  │   threshold methodology                                      │
│  └── Artifact: calibration_adoptions row + bundle               │
│                                                                 │
│  ARCHIVE                                                        │
│  ├── When: Experiment completion (Day 30)                       │
│  ├── What: All snapshots included in experiment evidence bundle │
│  └── Purpose: Reproducibility — future operator can replay       │
│      calibration analysis from archived snapshots               │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Unified vs Split

A single unified snapshot serves all consumers. The consumer determines purpose by context:

| Consumer | Purpose | How it reads the snapshot |
|----------|---------|--------------------------|
| Reflection Clock (create) | Calibration evidence | Writes during REFLECTING |
| CalibrationAnalyzer | Statistical analysis | Reads transition_counts → AIC/BIC/χ² |
| ExecutionEngine | Crash recovery | Reads transition_counts → restore() |
| Operator (governance) | Adoption decision | Reads EvidenceReport (derived from snapshot) |
| Future auditor | Reproducibility | Reads from archive |

**The snapshot is one artifact. Its meaning changes with the consumer.** This is conceptually identical to how a CSV file can be "sales data" to Marketing, "tax evidence" to Accounting, and "regression input" to Data Science — same bytes, different contexts.

*Recommendation: Keep unified. Add a `created_by` column (e.g., "reflection_engine") for provenance without splitting.*

---

## 6. CONCEPTUAL ARCHITECTURE

### 6.1 Responsibility Map

| Responsibility | Natural Owner | Currently Owned By | Gap? |
|---------------|---------------|-------------------|------|
| Market discovery | Discovery Clock | Discovery Clock | ✅ |
| Raw data ingestion | Evidence Clock | Evidence Clock | ✅ |
| **State classification** | **Evidence Clock** | **Decision Clock** (MarketStateTracker) | **🔴 Gap** |
| Measurement calibration (threshold) | Evidence Clock (governance) | Decision Clock (strategy param) | **🔴 Gap** |
| Transition learning | Decision Clock | Decision Clock | ✅ |
| Signal generation | Decision Clock | Decision Clock | ✅ |
| Trade execution | Decision Clock | Decision Clock | ✅ |
| Post-execution analysis | Reflection Clock | Reflection Clock | ✅ |
| **Snapshot creation** | **Reflection Clock** | **Nobody** | **🔴 Gap** |
| Calibration analysis | Reflection Clock | Reflection Clock | ✅ |
| Threshold adoption | Governance (operator) | Governance (operator) | ✅ |

### 6.2 Gaps Identified

**Gap 1 — State Classification Ownership**: MarketStateTracker runs inside ExecutionEngine (Decision Clock). It should run inside Evidence Clock's capture pipeline. The Evidence Clock already has access to price data; it already normalizes raw events to MarketInput. Adding state classification is a natural extension: raw tick → MarketInput → MarketState (classified).

**Gap 2 — Measurement Calibration Ownership**: The threshold is currently a MarkovStrategy constructor parameter. It should be an Evidence Clock governance parameter, adopted by the operator during domain onboarding, frozen thereafter (or recomputed deterministically per ATR).

**Gap 3 — Snapshot Creation**: No clock currently creates strategy_snapshots. The Reflection Clock is the natural owner — it already creates reflection_reports, and snapshots are the statistical evidence underlying calibration assessments.

### 6.3 No Missing Clocks

All three gaps can be resolved within the existing four-clock architecture:

- Gap 1: Move MarketStateTracker from Decision Clock to Evidence Clock (conceptual migration — implementation may be phased)
- Gap 2: Add threshold as an Evidence Clock frozen governance parameter (like eligibility rules)
- Gap 3: Add snapshot creation to Reflection Clock's REFLECTING stage (Option D from Architectural Review)

**No fifth clock is needed.** The Calibration Clock was explicitly rejected (§6.3) as "a mode of Reflection at extended frequency." This analysis confirms that decision. Measurement calibration is a Governance activity performed during domain onboarding. Calibration analysis is a Reflection activity performed post-execution. Neither requires a dedicated clock.

### 6.4 Conceptual Flow (Refined)

```
DOMAIN ONBOARDING (pre-Day-0, operator-governed):
  Governance → adopts threshold methodology (e.g., ATR-based with α=0.5)
  Governance → freezes as Evidence Clock measurement parameter

EACH SESSION (Day 0-30, automated):
  Evidence Clock:
    → captures raw ticks (WebSocket)
    → classifies: MarketState(price, state=UP/DOWN/NEUTRAL, prev_state)
    → persists: event_store + classified states
  
  Decision Clock:
    → reads classified states
    → MarkovStrategy learns transitions
    → generates signals
    → executes trades
  
  Reflection Clock:
    → reads trades + classified states
    → creates snapshot (transition matrix from classified states)
    → analyzes: AIC, BIC, χ², persistence, entropy
    → persists: reflection_reports + strategy_snapshots

POST-EXPERIMENT (Day 30, operator-governed):
  Governance → calibrate review (reads snapshots)
  Governance → adopts state space configuration (calibrate adopt)
  Governance → Architecture Contract amended with adopted config
```

---

## 7. UNRESOLVED QUESTIONS

### 7.1 Implementation Questions (deferred to SDD)

1. **State persistence format**: Should classified states be stored in a new `market_states` table, as additional columns in `event_store`, or derived on-the-fly from raw events? The architectural answer is "Evidence Clock persists classified states separately" — but the persistence format is an SDD decision.

2. **ATR computation window**: What N-period ATR is optimal for crypto tick data? Wilder's 14-period is for daily bars. For sub-second ticks, the window must be empirically determined.

3. **α governance constant**: What α multiplier produces the best state distribution? This is the parameter the operator would adopt — it must be determined through pre-experiment calibration.

4. **Backward compatibility**: The current implementation has Decision Clock running MarketStateTracker. Migrating to Evidence Clock ownership without breaking the running experiment requires a transitional design.

### 7.2 Architectural Questions (open)

1. **Is ATR-based threshold truly domain-agnostic?** It works for continuous price data (crypto, stocks, forex) but not for binary outcome markets (Polymarket). Should the threshold methodology itself be domain-specific? The Architecture Contract §30 allows domain-specific configurations — this fits.

2. **Does state classification migration require a clock interface change?** Currently, clocks communicate via database tables (unidirectional, data-flow coordination per §6.3). If Evidence Clock writes classified states and Decision Clock reads them, this is consistent with the existing pattern. No interface change needed.

3. **Should the CalibrationAnalyzer read from snapshots or directly from classified states?** The snapshot captures the transition matrix at tick N. The analyzer currently reads from snapshots. If snapshots are created by Reflection, the analyzer's dependency is correct. Direct analysis of classified states would be a separate (complementary) capability.

### 7.3 Governance Questions (open)

1. **Who validates the measurement instrument?** The operator adopts the threshold methodology. But who validates that the methodology produces valid measurements? This is a governance gap: the operator can adopt a bad threshold. The Calibration Framework provides evidence (AIC, BIC, χ²) but does not reject invalid configurations.

2. **What is the amendment process for measurement methodology?** Architecture Contract §28 provides the mechanism. But the amendment should distinguish between "strategy parameter change" (which affects Decision Clock) and "measurement methodology change" (which affects Evidence Clock). These are different amendment types.

### 7.4 Scientific Questions (open)

1. **Incommensurability across thresholds**: If the experiment ever changes threshold methodology, states classified under different methodologies are incommensurable. "UP at 0.1%" ≠ "UP at 0.001%". How should the architecture prevent or manage this? The current answer ("don't change it") is procedural, not architectural.

2. **Measurement drift**: Even with a deterministic ATR-based threshold, the measurement instrument's behavior changes as market volatility changes. Is this a feature (adaptation) or a bug (instrument drift)? The Adaptive Market Hypothesis (Lo, 2004) suggests it's a feature — markets evolve, measurement should too. But this conflicts with the classical experimental design principle of fixed instruments.

---

## 8. CONFIDENCE ASSESSMENT

| Finding | Confidence | Basis |
|---------|-----------|-------|
| Threshold is measurement calibration, not strategy parameter | **HIGH** | Conceptual distinction between measurement and model; consistent with Architecture Contract §6.1 clock responsibilities |
| Evidence Clock should own state classification | **HIGH** | "Time-series data ingestion" includes classification; MarketStateTracker is measurement, not decision |
| Reflection Clock should own snapshots | **HIGH** | Consistent with Architectural Review, Research Report, and RFC-004 |
| ATR-based threshold is appropriate for crypto | **MEDIUM-HIGH** | Wilder (1978) established methodology; crypto applicability empirically untested for Trady AI |
| No fifth clock needed | **HIGH** | All responsibilities map to existing four clocks |
| Unified snapshot is architecturally correct | **MEDIUM** | Single artifact serves multiple consumers; ML industry precedent; Portable OS A5 |
| Pre-Day-0 calibration is stronger science | **MEDIUM** | Logically consistent; no empirical comparison with embedded pilot design |
| Incommensurability risk is architectural, not procedural | **LOW** | This is a real risk but current mitigation (freeze) is procedural; architectural solution unexplored |

---

**This discovery report identifies three conceptual gaps in the current architecture, all resolvable within the existing four-clock model. The central insight — threshold is a measurement instrument, not a strategy parameter — reframes the entire calibration problem and provides a clear path to architectural resolution.**
