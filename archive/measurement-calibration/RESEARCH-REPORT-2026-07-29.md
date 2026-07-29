# SCIENTIFIC AND ARCHITECTURAL RESEARCH REPORT — Paper Trading Calibration Barrier

> **Date**: 2026-07-29 | **Type**: Evidence-Driven Architectural Investigation
> **Authority**: Trady AI Architecture + Scientific Literature + Industry Practice
> **Artifacts Reviewed**: STATUS-REPORT-2026-07-29, ARCHITECTURAL-REVIEW-2026-07-29

---

## 1. EXECUTIVE SUMMARY

### 1.1 Key Findings

1. **Frozen threshold at 0.1% produces low-quality evidence** for crypto tick data. The experiment's measurement instrument is calibrated for Polymarket football (hours-long resolution windows), not crypto (sub-second ticks). This is a **measurement validity problem**, not a strategy optimization problem. [Scientific Literature + Trady AI Architecture]

2. **A "pilot → confirmatory" two-phase design** is academically supported. The FDA (2019) explicitly allows adaptive clinical trial designs with pre-specified adaptation rules. In our context: a short pilot phase to find the measurement range, followed by a frozen confirmatory phase. This preserves scientific validity while acknowledging that initial parameters were uninformed. [Scientific Literature]

3. **Strategy Snapshots are model checkpoints with tripartite identity**: they simultaneously serve as execution state (for reconstruction), scientific evidence (for calibration), and recovery artifacts (for crash recovery). Splitting them into three specialized artifacts would violate Portable OS A5 (Simplicity). A single snapshot with bounded context-aware consumers is architecturally superior. [Architectural Reasoning]

4. **The Architectural Review correctly identified** that snapshots belong to Reflection Clock and threshold must be governed. However, it over-indexed on contract preservation at the expense of measurement validity. A frozen contract applied to an invalid measurement instrument is procedural correctness without scientific value. [Critical Review]

5. **ATR-based adaptive thresholds** (Wilder, 1978) are a deterministic, non-AI method that adjusts threshold to market volatility. This is academically established and aligns with Portable OS A1 (Deterministic-First). An ATR-based threshold would automatically produce ~0.001%-0.01% thresholds for BTC without manual tuning. [Industry Practice + Scientific Literature]

### 1.2 Recommendations

| # | Recommendation | Basis |
|---|---------------|-------|
| 1 | **Adopt a two-phase design**: 2-day pilot (threshold discovery) + 28-day confirmatory (frozen calibrated threshold) | FDA Adaptive Design Guidance; Adaptive Market Hypothesis |
| 2 | **Implement ATR-based threshold** for the confirmatory phase, governed by operator adoption | Wilder (1978); Portable OS A1, RFC-007 |
| 3 | **Persist snapshots in REFLECTING stage** (Option D), owned by Reflection Clock | RFC-004, Architectural Review finding |
| 4 | **Maintain snapshot as a single multi-purpose artifact** | Portable OS A5; industry practice (ML model checkpoints) |
| 5 | **Amend Architecture Contract §28** to document the pilot→confirmatory design as D-003 | Architecture Contract amendment mechanism |

---

## 2. SCIENTIFIC ANALYSIS — Q1: FROZEN VS ADAPTIVE THRESHOLD

### 2.1 The Measurement Problem

The current threshold (0.1%) classifies 99% of crypto ticks as NEUTRAL. This is not a strategy failure — it is a measurement failure. The instrument (threshold-based state classifier) is calibrated for a domain where meaningful price movements occur over hours (Polymarket football: binary outcome, 90-min resolution), not seconds (crypto: continuous tick-by-tick, sub-second resolution).

**Source**: Bybit API confirms `tickSize: 0.1` for BTCUSDT. At ~$87,000/BTC, one tick = $0.10 = 0.000115% of price. The current threshold of 0.1% requires 870 consecutive ticks in the same direction to register a single state transition.

### 2.2 Scientific Validity of Frozen Parameters

In experimental design, **internal validity** requires that the measurement instrument is appropriate for the phenomenon being measured. A thermometer calibrated for body temperature (35-42°C) cannot validly measure room temperature (15-30°C) — not because the thermometer is broken, but because its calibration range doesn't cover the measurement domain.

The Architecture Contract §16.1 freezes `threshold_pct=0.001` — but this freeze was based on Polymarket football markets (§2.3: "binary outcome, short resolution cycle, high data density"). The contract was amended for multi-domain support (§30) but the threshold was carried over without re-calibration for crypto.

**Conclusion**: Continuing with 0.1% threshold produces **internally valid but scientifically uninformative** evidence. Each session is deterministic, reproducible, and auditable — but the data has near-zero signal. This satisfies Portable OS A1 (determinism) while violating Portable OS A7: "Validate uncertainty before scaling complexity." The primary uncertainty — "can the Markov engine detect patterns in crypto tick data?" — cannot be answered with the current threshold.

*Basis: Campbell & Stanley (1963), Experimental and Quasi-Experimental Designs for Research; Shadish, Cook & Campbell (2002), Experimental and Quasi-Experimental Designs for Generalized Causal Inference.*

### 2.3 Signal-to-Noise Ratio Analysis

| Threshold | NEUTRAL % (est.) | Transitions per 60s session | Markov learnable? |
|-----------|-----------------|----------------------------|-------------------|
| 0.1% | ~99% | ~0.2 | ❌ No |
| 0.01% | ~90% | ~2 | ⚠️ Marginal |
| 0.005% | ~70% | ~6 | ✅ Yes |
| 0.001% | ~40% | ~12 | ✅ Strong |
| 0.0005% | ~20% | ~16 | ⚠️ Noise boundary |
| 0.0001% | ~5% | ~19 | ❌ Noise dominates |

The sweet spot for a 60-second crypto session is 0.001%-0.005%, where the Markov engine sees 6-12 state transitions per session — sufficient to learn first-order patterns within one session's warmup period (50 ticks).

*Basis: Derived from Bybit tickSize data + binomial approximation of tick-by-tick price movement. Empirical validation pending from accumulated event_store data.*

---

## 3. Q2: MID-EXPERIMENT PARAMETER ADJUSTMENT

### 3.1 Academic Precedent

**Clinical Trials — FDA Adaptive Design Guidance (2019)**:
The FDA explicitly permits "adaptive clinical trials" where parameters (sample size, treatment arms, randomization ratios) are modified during an ongoing trial, provided:
1. The adaptation rules are **pre-specified** before data collection begins
2. The adaptation does not **inflate Type I error** (false positive rate)
3. An **Independent Data Monitoring Committee** reviews interim results
4. The adaptation is documented as a **protocol amendment**

Our analog: the "adaptation rule" is the threshold calibration methodology (AIC/BIC/χ²). The "Type I error" control is that we're in dry_run mode. The "Data Monitoring Committee" is the operator reviewing `calibrate review` output. The "protocol amendment" is Architecture Contract §28.

**Machine Learning — Hyperparameter Tuning**:
In supervised learning, hyperparameters are tuned on a **validation set**, never on the training set. The final model is evaluated on a **held-out test set** with frozen hyperparameters. This three-way split (train/validate/test) is the ML analog of our pilot/confirmatory design.

**Economics — Adaptive Market Hypothesis (Lo, 2004)**:
"The degree of market efficiency is related to environmental factors characterizing market ecology." Implication: parameters that work in one market regime may not work in another. Fixed parameters are only valid if the market regime is stationary. For crypto, which exhibits evolving efficiency (Khuntia & Pattanayak, 2018), some degree of adaptation is theoretically justified.

### 3.2 Pilot → Confirmatory Two-Phase Design

This is the academically strongest approach:

```
Phase 1 — PILOT (Days 1-2):
  - Purpose: Discover viable threshold range for crypto
  - Method: Test N thresholds (0.0005%, 0.001%, 0.005%, 0.01%, 0.05%)
  - Evidence: AIC, BIC, Markov χ², persistence, entropy per threshold
  - Output: Recommended threshold with statistical justification
  - Governance: Operator reviews, adopts via calibrate adopt
  
Phase 2 — CONFIRMATORY (Days 3-30):
  - Purpose: Validate adopted threshold with frozen parameters
  - Method: Fixed threshold based on pilot evidence
  - Evidence: 2,688 sessions with full audit trail
  - Output: Calibration readiness assessment
  - Governance: Frozen per Architecture Contract
```

**Why this preserves scientific validity**:
1. The pilot phase is **declared as exploratory** — its data is not part of the 30-day confirmatory evidence
2. The confirmatory phase uses **frozen parameters** — satisfying Architecture Contract §16.1
3. The adaptation rule is **pre-specified** (AIC/BIC/χ² comparison) — satisfying FDA criteria
4. The operator makes the adoption decision — satisfying RFC-007 (Human Sovereignty)
5. The two phases are **clearly segmented** — data from each phase is labeled with its threshold

*Basis: FDA (2019), Adaptive Designs for Clinical Trials of Drugs and Biologics; Kohavi et al. (1995), A Study of Cross-Validation and Bootstrap for Accuracy Estimation and Model Selection; Lo (2004), The Adaptive Markets Hypothesis.*

---

## 4. Q3: RESTART VS CONTINUE

### 4.1 Comparative Analysis

| Factor | Continue (keep 1,300 events) | Restart (clean DB, Day 0) |
|--------|------------------------------|---------------------------|
| **Data quality** | 1,300 events of ~99% NEUTRAL | Fresh data with calibrated threshold |
| **Scientific validity** | Mixed-threshold evidence contaminates analysis | Clean, single-threshold evidence |
| **Time cost** | 0 — already accumulated | ~2 days to re-accumulate |
| **Statistical power** | Very low (few transitions) | High (frequent transitions) |
| **Audit trail** | Messy: threshold changed mid-stream | Clean: threshold frozen from Day 0 |
| **Contract compliance** | Requires amendment for mixed thresholds | Requires amendment for new threshold |

### 4.2 Recommendation

**Restart after pilot.** The 2-day pilot produces threshold evidence. On Day 3, clean DB, adopt calibrated threshold, freeze for 28 days. This produces 28 days of clean, single-threshold evidence — stronger than 30 days of mixed-threshold data or 30 days of uninformative data.

The 1,300 events from Day 1-2 are archived as pilot evidence, not discarded. They served their purpose: validating that the pipeline works and producing the initial calibration analysis.

---

## 5. Q4: NATURE OF STRATEGY SNAPSHOTS

### 5.1 Multiple Simultaneous Identities

A Strategy Snapshot captures the complete statistical state of a Markov persistence engine at a point in time. It contains:

| Component | What it represents |
|-----------|-------------------|
| `transition_counts` | N×N matrix of observed state transitions |
| `state_counts` | N-vector of state visitation frequencies |
| `threshold_pct` | Classification threshold in effect |
| `warmup_ticks` | Warmup period |
| `state_space_size` | Number of states (N) |
| `state_generator` | Generator name |
| `tick_number` | Monotonically increasing observation count |

### 5.2 Which Interpretation Is Correct?

| Interpretation | Is it true? | Evidence |
|---------------|------------|----------|
| **Execution state** | ✅ Yes | The transition matrix IS the execution state of a Markov chain. A DTMC is fully defined by (S, P, π₀) where P is the transition matrix. |
| **Serialized strategy state** | ✅ Yes | `get_state_summary()` serializes `_transition_counts`, `_state_counts`, and config — this is serialization of MarkovPersistenceEngine's internal state. |
| **Scientific evidence** | ✅ Yes | AIC, BIC, χ², persistence, and entropy are computed FROM the transition matrix. The snapshot IS the primary evidence artifact for calibration. |
| **Calibration artifact** | ✅ Yes | The Calibration Framework's `analyze()` method takes a snapshot as input and produces an EvidenceReport. |
| **Recovery artifact** | ✅ Yes | `load_latest_snapshot()` and `restore()` in MarkovPersistenceEngine can reconstruct the engine's state from a snapshot. |
| **Statistical checkpoint** | ✅ Yes | "Checkpoint" is the standard ML term for saving model state for later resumption. The snapshot saves the transition matrix at tick_number N. |

**Conclusion**: A Strategy Snapshot is **all six simultaneously**. This is not a design flaw — it is the mathematical nature of a Markov chain: the transition matrix simultaneously defines the model (execution), serves as evidence for its quality (calibration), and enables reconstruction (recovery).

*Basis: Formal definition of DTMC — a Markov chain with finite state space S is fully characterized by its transition probability matrix P and initial distribution. The transition count matrix C approaches P × (total observations) as observations → ∞ (MLE). The snapshot captures C at a finite observation count.*

---

## 6. Q5: SNAPSHOT — UNIFIED OR SPLIT?

### 6.1 The Case for Splitting

| Artifact | Purpose | Consumer | Frequency |
|----------|---------|----------|-----------|
| Runtime snapshot | Crash recovery (restore engine state) | ExecutionEngine | Every N ticks |
| Calibration snapshot | Scientific evidence (AIC/BIC/χ²) | CalibrationAnalyzer | Once per day or per session |
| Recovery snapshot | Session reconstruction | Session | On session interruption |

### 6.2 The Case Against Splitting

All three artifacts contain the **same underlying data**: the transition count matrix. Splitting creates three copies of the same mathematical object, stored at potentially different tick_numbers, with different provenance. This introduces:

1. **Reconciliation burden**: Which snapshot is authoritative at tick N?
2. **Storage waste**: 3 copies of the same N×N matrix
3. **Provenance confusion**: Was snapshot #47 from runtime, calibration, or recovery?
4. **Portable OS A5 violation**: Three artifacts for one concept = unnecessary complexity

### 6.3 Recommendation: Unified Snapshot with Context Column

Keep a single `strategy_snapshots` table. Add a `purpose` column (`runtime_recovery`, `calibration_evidence`, `session_recovery`) to disambiguate without duplicating. Each consumer reads snapshots filtered by purpose.

This is the industry standard approach: ML frameworks (PyTorch, TensorFlow) save a single checkpoint file that serves both recovery and analysis. The consumer determines how to interpret it.

*Basis: PyTorch `torch.save()` saves model state_dict — used both for resuming training and for model analysis. The file is the same; the consumer's intent differs.*

---

## 7. Q6-Q7: CLOCK OWNERSHIP + MARKOV PERSISTENCE

### 7.1 Responsibility Distribution

| Responsibility | Owner | Justification |
|---------------|-------|---------------|
| **Snapshot creation** | Reflection Clock (REFLECTING stage) | Snapshots are calibration evidence. Reflection owns evidence per RFC-004. |
| **Snapshot persistence** | Reflection Clock → `strategy_snapshots` table | Same clock that writes `reflection_reports`. Consistent ownership. |
| **Snapshot consumption (calibration)** | Reflection Clock → CalibrationAnalyzer | RFC-004: Reflection owns "calibration assessments" |
| **Snapshot consumption (recovery)** | Decision Clock → ExecutionEngine.restore() | RFC-001: Core owns "deterministic execution recovery" |
| **Snapshot consumption (audit)** | Governance (human operator) | RFC-007: Operator owns "governance review" |

### 7.2 Markov Persistence — Industry Best Practice

In Hidden Markov Model implementations (hmmlearn, pomegranate, ghmm), the persisted state includes:

| Component | hmmlearn | pomegranate | Trady AI |
|-----------|----------|-------------|----------|
| Transition matrix (A) | ✅ `model.transmat_` | ✅ | ✅ `transition_counts` |
| Emission probabilities (B) | ✅ `model.means_`, `covars_` | ✅ | N/A (no emissions) |
| Initial distribution (π) | ✅ `model.startprob_` | ✅ | ❌ Not persisted |
| Training iterations | ✅ `model.n_iter_` | ✅ | ✅ `tick_number` |
| Model hyperparameters | ✅ `model.n_components` | ✅ | ✅ `state_space_size`, `warmup_ticks`, `threshold_pct` |

**Gap identified**: Trady AI does not persist the **initial state distribution** (π). This would be `_state_counts / _total_obs`. Not critical for calibration (AIC/BIC use transition matrix only) but relevant for full model reconstruction.

*Basis: hmmlearn 0.3.0 documentation — `MultinomialHMM` attributes; pomegranate 1.0.0 documentation — `HiddenMarkovModel` serialization; Rabiner (1989), A Tutorial on Hidden Markov Models and Selected Applications in Speech Recognition.*

---

## 8. Q8: ADAPTIVE THRESHOLD METHODOLOGIES

### 8.1 ATR-Based Threshold (Wilder, 1978)

The Average True Range measures market volatility independent of trend direction. An ATR-based threshold adapts to market conditions:

```
threshold_pct(t) = α × ATR(t) / price(t)
```

Where α is a calibration constant (e.g., α = 0.1 means threshold = 10% of ATR).

**Deterministic guarantee**: ATR is computed from (high, low, close) prices using a fixed formula. For a given price history, ATR is deterministic. Therefore, an ATR-based threshold preserves Portable OS A1.

**Crypto applicability**: ATR adapts naturally to crypto's varying volatility regimes. During high volatility (BTC moving $2,000/day), threshold widens. During low volatility ($200/day), threshold narrows. This prevents the "99% NEUTRAL" problem regardless of market conditions.

### 8.2 Volatility-Based Threshold

Standard deviation of log returns over a rolling window:

```
threshold_pct(t) = β × σ_N(t)
```

Where σ_N(t) is the N-period standard deviation of log returns. Similar determinism guarantee as ATR.

### 8.3 Statistical Process Control (Shewhart, 1931)

Control limits based on process mean and standard deviation:

```
UCL = μ + kσ
LCL = μ - kσ
```

Where k is typically 3 (three-sigma limits). A price movement beyond kσ is "out of control" — a significant state transition. This maps naturally to UP (above UCL) / DOWN (below LCL) / NEUTRAL (within limits).

**Determinism guarantee**: μ and σ are computed from historical data. For a fixed lookback window, they are deterministic. k is a frozen governance parameter.

### 8.4 Recommendation

**ATR-based adaptive threshold** with operator-adopted α constant. This is:
- ✅ Deterministic (Portable OS A1)
- ✅ Academically established (Wilder, 1978)
- ✅ Widely used in industry (position sizing, stop-loss placement)
- ✅ No AI/ML dependency (RFC-005 compliant)
- ✅ Self-adjusting to volatility regimes (Adaptive Market Hypothesis aligned)
- ✅ Single governance parameter (α) — operator adopts, then frozen

---

## 9. Q9: GOVERNANCE IMPLICATIONS

### 9.1 Governance Models

| Model | Description | Scientific Reproducibility |
|-------|-------------|--------------------------|
| **Operator adopts recommendation** | `calibrate review` → operator reviews → `calibrate adopt --confirm` | ✅ Full provenance: who adopted, when, why, based on what evidence |
| **Automatic adoption** | System auto-adopts best threshold | ❌ No human attribution. Who decided? Based on what criteria? |
| **New experiment** | Each threshold test is a separate experiment | ✅ Cleanest evidence but impractical for rapid iteration |
| **Architecture amendment** | Each threshold change is a contract amendment | ✅ Strongest governance but slowest iteration |

### 9.2 Recommendation

**Operator adopts recommendation with Architecture Contract amendment**. This is the existing mechanism (`calibrate adopt` + Architecture Contract §28) and is most compatible with RFC-007 (Human Sovereignty) and scientific reproducibility. The amendment log provides auditable provenance of every parameter change.

---

## 10. Q10: CRITICAL REVIEW OF THE ARCHITECTURAL REVIEW

### 10.1 Agreement Points

| Architectural Review Finding | Verdict | Reason |
|------------------------------|---------|--------|
| Snapshots belong to Reflection Clock | ✅ Agree | Consistent with RFC-004 ownership of "evaluation lineage" |
| Session should not own persistence | ✅ Agree | Session is a cross-clock orchestrator per Architecture Contract §6.2 |
| Option C violates clock boundaries | ✅ Agree | Placing snapshot writes in EXECUTING creates cross-clock coupling |
| Threshold is a governance artifact | ✅ Agree | Must be operator-adopted, not auto-configured |
| `strategy_snapshots` is architecturally orphaned | ✅ Agree | No clock currently owns it |

### 10.2 Disagreement Points

| Architectural Review Claim | Counter-Argument | Basis |
|---------------------------|-----------------|-------|
| "Threshold must remain frozen at 0.1% per §16.1" | The freeze was based on Polymarket football domain, not crypto. §16.1 says "fixed parameters for the 30-day experiment" — but the experiment domain changed via §30 (Multi-Domain Architecture). The threshold was never re-calibrated for the new domain. | Architecture Contract §30; Bybit tickSize data |
| "Calibration must be post-experiment per §17.2" | §17.2 describes the calibration GATE (30 reports → ready_for_calibration), not a prohibition on pre-experiment calibration. A pilot phase to set the measurement instrument is calibration OF the instrument, not calibration FROM the evidence. These are distinct activities. | Distinction between "instrument calibration" and "evidence calibration" |
| "Option D preserves all Portable OS principles" | Option D preserves architectural principles but fails A7 (Validate Uncertainty First). The primary uncertainty — "can the Markov engine detect patterns in crypto?" — remains unvalidated. A7 says validate uncertainty BEFORE scaling complexity. Option D preserves complexity without validating the uncertainty. | Portable OS A7 |
| "Mid-experiment threshold change breaks determinism" | If the change is pre-specified (pilot→confirmatory design) and each phase has a FROZEN threshold, determinism is preserved WITHIN each phase. Data is labeled with the threshold that produced it. The experiment becomes a segmented time series, not a contaminated one. | FDA Adaptive Design Guidance (2019) |

### 10.3 The Architectural Review's Blind Spot

The Architectural Review correctly identified that the Architecture Contract freezes parameters. But it did not question whether the frozen parameter was **valid for the measurement domain**. This is the difference between:

- **Procedural correctness**: "The contract says it's frozen, so it must stay frozen."
- **Scientific validity**: "Is the frozen parameter appropriate for what we're measuring?"

A frozen contract applied to an invalid measurement instrument is procedural correctness without scientific value. The Architecture Contract §30 added multi-domain support but did not re-calibrate domain-specific parameters. This is the gap the Architectural Review missed.

### 10.4 Does Option D Survive?

**Option D is architecturally correct but scientifically incomplete.** It solves the snapshot orphan problem but leaves the threshold validity problem unaddressed. A complete solution requires:

1. Option D (snapshot persistence in REFLECTING) ✅
2. Pilot phase for threshold discovery (new)
3. Confirmatory phase with adopted frozen threshold (new)
4. Architecture Contract amendment documenting the two-phase design (new)

---

## 11. FINAL RECOMMENDATIONS

### 11.1 Immediate (authorized without amendment)

**Implement Option D**: Persist `strategy_snapshots` in the REFLECTING stage. This is architecturally correct per RFC-004 and addresses the immediate orphan problem.

### 11.2 Short-Term (requires Architecture Contract amendment)

**Adopt pilot→confirmatory design and ATR-based threshold**:

| Step | Action | Governance |
|------|--------|-----------|
| 1 | Amend Architecture Contract §28: document two-phase design as D-003 | Operator approves amendment |
| 2 | Run 2-day pilot: test N thresholds, collect snapshots | Auto (crontab), operator reviews |
| 3 | `calibrate review` → operator adopts best threshold | `calibrate adopt --confirm` |
| 4 | Clean DB, restart with adopted frozen threshold | New Day 0 |
| 5 | 28-day confirmatory experiment | Frozen, autonomous |
| 6 | Day 28: calibration gate activates (§17.2) | Reflection Clock |

### 11.3 Medium-Term

**Implement ATR-based adaptive threshold** with operator-adopted α constant. This eliminates the need for manual threshold tuning across market regimes.

---

## 12. CONFIDENCE LEVELS

| Finding | Confidence | Basis |
|---------|-----------|-------|
| Frozen 0.1% is scientifically invalid for crypto | **VERY HIGH** | Bybit tickSize data (empirical) + measurement validity theory |
| Pilot→confirmatory design is academically supported | **HIGH** | FDA Adaptive Design Guidance (2019) + ML hyperparameter tuning practice |
| ATR-based threshold is deterministic | **VERY HIGH** | Wilder (1978) formula is mathematically deterministic |
| Strategy Snapshots have multiple simultaneous identities | **HIGH** | DTMC formal definition + industry practice |
| Unified snapshot is superior to split artifacts | **HIGH** | Portable OS A5 + ML framework precedent |
| Architectural Review's contract interpretation is partially correct | **MEDIUM** | The review correctly identifies ownership but over-indexes on procedural freeze |
| Restart after pilot produces stronger evidence than continuing | **HIGH** | Statistical power analysis + measurement validity |

---

## 13. OPEN QUESTIONS

1. **ATR period**: What ATR lookback period is optimal for crypto tick data? Wilder recommends 14 periods for daily data, but our "period" is sub-second ticks. Empirical calibration needed.

2. **α constant for ATR threshold**: What multiplier of ATR produces the optimal state distribution? This is the governance parameter the operator would adopt.

3. **Pilot duration**: Is 2 days sufficient to discover viable thresholds? Depends on event density — with ~94 events/hour, 2 days = ~4,500 events, sufficient for 5 thresholds × 50 warmup ticks each.

4. **Segmented evidence aggregation**: If the experiment has two phases (pilot + confirmatory) with different thresholds, how should the Day 30 calibration gate aggregate evidence? Should it use only confirmatory data, or all data with threshold as a covariate?

---

**This report was produced through evidence-driven architectural investigation. All conclusions distinguish between Trady AI architectural authority, scientific literature, and independent architectural reasoning.**
