# Delta for Evidence Pipeline

**Extends**: `reflection-systems` (Module 2: Reflection Analyzers, Module 4: reflect() entry point)
**RFC**: RFC-004 §Statistical Evidence, CALIBRATION-FRAMEWORK-2026-07-23.md
**Package**: `src/trady_ai/reflection/calibration/`

---

## ADDED Requirements

### Requirement: CalibrationAnalyzer

The system SHALL add `CalibrationAnalyzer` as an injectable analyzer in the
`ReflectionEngine` pipeline. It SHALL consume transition counts + state sequence and
produce a deterministic `EvidenceReport`.

#### Scenario: Analyzer runs in deterministic pipeline order

- GIVEN ReflectionEngine with CalibrationAnalyzer injected after DriftAnalyzer
- WHEN `reflect()` is called
- THEN CalibrationAnalyzer runs in its pipeline position, before report assembly

### Requirement: AIC Computation

`CalibrationAnalyzer.aic(transition_counts, state_sequence) → float` SHALL compute:

$$AIC = -2\ln(L) + 2k \quad\text{where } k = |S|(|S|-1)$$

where $L$ is the Markov chain likelihood: $\prod_{i,j} p_{ij}^{n_{ij}}$ using MLE
$\hat{p}_{ij} = n_{ij}/\sum_j n_{ij}$. AIC MUST be deterministic — same inputs produce
identical float.

#### Scenario: More states penalized

- GIVEN same dataset, |S|=3 AIC=120.5 vs |S|=5
- WHEN both computed
- THEN |S|=5 AIC > |S|=3 AIC unless likelihood improvement justifies the extra params

### Requirement: BIC Computation

`CalibrationAnalyzer.bic(transition_counts, state_sequence, n) → float` SHALL compute:

$$BIC = -2\ln(L) + k\ln(n) \quad\text{where } n = \text{total observations}$$

#### Scenario: BIC stronger penalty than AIC

- GIVEN n=1000 observations, |S|=3 (k=6)
- WHEN AIC and BIC both computed
- THEN BIC penalty = 6·ln(1000) ≈ 41.4 vs AIC penalty = 12

### Requirement: Markov χ² Test

`CalibrationAnalyzer.markov_order_test(state_sequence, |S|, α=0.05) → dict` SHALL
implement the Billingsley χ² test for first-order Markov property:

$$ \chi^2 = \sum_{i,j} \frac{(n_{ij} - e_{ij})^2}{e_{ij}} \quad\text{df}=|S|(|S|-1) $$

Returns: `{statistic, p_value, df, reject_null, significance_level}`.

#### Scenario: Strong Markov signal

- GIVEN a state sequence with clear first-order transitions
- WHEN markov_order_test(α=0.05) called
- THEN reject_null=True, p_value < 0.001

### Requirement: State Persistence and Entropy

The analyzer SHALL compute per-state:
- **Mean residence time**: `1/(1 - p_{ii})` ticks (expected, per diagonal)
- **Conditional entropy**: $H(X_{n+1}|X_n) = -\sum_i \pi_i \sum_j p_{ij}\log_2 p_{ij}$ where $\pi$ is the stationary distribution

#### Scenario: Entropy zero for deterministic chain

- GIVEN a chain where each state transitions deterministically to one next state
- WHEN conditional_entropy() computed
- THEN H = 0.0

### Requirement: EvidenceReport

`EvidenceReport` dataclass SHALL contain: `aic`, `bic`, `markov_test`, `state_persistence`
(dict), `conditional_entropy`, `transition_counts`, `state_sequence_length`,
`computed_at`. All fields are deterministic — same inputs → identical values.

#### Scenario: Serialize to JSON deterministically

- GIVEN the same transition matrix and sequence processed twice
- WHEN `json.dumps(report)` called on both
- THEN byte-identical output

---

## MODIFIED Requirements

### Requirement: ReflectionEngine Orchestration (MODIFIED)

`ReflectionEngine` SHALL accept an optional `calibration_analyzer: CalibrationAnalyzer`
in its constructor. When provided, `reflect()` SHALL append `evidence_report` to the
`ReflectionReport` and persist it alongside other report data.

(Previously: no calibration analyzer in the pipeline)

#### Scenario: Engine runs with calibration analyzer

- GIVEN ReflectionEngine with CalibrationAnalyzer injected
- WHEN reflect(scope="weekly", domain="PM-5M") called
- THEN ReflectionReport contains evidence_report field with AIC, BIC, entropy, χ²
