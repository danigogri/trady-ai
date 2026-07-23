# Delta for Markov Persistence Engine

**Extends**: `markov-persistence-engine` | **RFC**: RFC-003 §Markov Infrastructure, RFC-004
**Package**: `src/trady_ai/strategies/markov/persistence.py`

---

## ADDED Requirements

### Requirement: N-State Matrix Construction

The engine SHALL accept `state_space_size: int` at construction, defaulting to 3. The
transition matrix SHALL be `|S| × |S|` numpy int64. `_state_counts` SHALL be length `|S|`.

| Parameter | Default | Constraint |
|-----------|---------|------------|
| `state_space_size` | 3 | ≥ 2, ≤ 100 |
| `state_generator` | `DirectionalStateGenerator(3)` | MUST implement `StateGenerator` ABC |

#### Scenario: 5-state engine operates correctly

- GIVEN `MarkovPersistenceEngine(state_space_size=5)`
- WHEN 100 ticks processed with a 5-state generator
- THEN transition_counts.shape == (5, 5) AND state_counts.shape == (5,)
- AND `evaluate()` returns valid Signal with probabilities length 5

#### Scenario: Invalid |S| rejects early

- GIVEN `state_space_size=1`
- WHEN engine constructed
- THEN raises `ValueError("state_space_size must be ≥ 2")`

### Requirement: Abstract State Indices

The engine SHALL operate exclusively on integer state indices. It SHALL NOT reference
semantic labels ("UP", "DOWN", etc.) in transition logic. Label mapping belongs to
`StateGenerator.state_labels` only.

#### Scenario: Engine evaluates using indices only

- GIVEN engine with |S|=4, current state index 2
- WHEN `evaluate()` called
- THEN it reads row 2 of transition matrix, computes probs via argmax on indices, returns Signal with direction from generator labels

---

## MODIFIED Requirements

### Requirement: R1 — V1 Markov Variants (MODIFIED)

DirectionalPersistence and VolatilityPersistence SHALL delegate state classification to
their configured `StateGenerator` implementation instead of hardcoding `STATE_INDEX` and
`VOLATILITY_INDEX` dicts. The internal mapping dicts move into `DirectionalStateGenerator`
and `VolatilityStateGenerator` respectively.

(Previously: hardcoded module-level `STATE_INDEX`, `VOLATILITY_INDEX`, `DIRECTION_MAP`, `VOLATILITY_DIR_MAP` dicts)

| Variant | Default Generator | |S| |
|---------|------------------|-----|
| DirectionalPersistence | `DirectionalStateGenerator` | 3 |
| VolatilityPersistence | `VolatilityStateGenerator` | 3 |

#### Scenario: DirectionalPersistence matches Fase 2 (preserved)

- GIVEN same 100 MarketState inputs
- WHEN DirectionalPersistence and legacy MarkovStrategy both process them
- THEN identical Signal outputs (field-by-field) — zero assertion changes

#### Scenario: VolatilityPersistence classifies states (preserved)

- GIVEN MarketState with increasing price range
- WHEN `update(state)` called via generator
- THEN volatility state transitions to HIGH if range exceeds threshold

---

## PRESERVED Requirements

| Req | Title | Notes |
|-----|-------|-------|
| R2 | Signal Generation Contract | Unchanged — argmax, confidence, UUID5, warmup |
| R3 | Internal Contracts Only | Unchanged — MarketState input only |
| R4 | Statistical Traceability | Unchanged — snapshots persisting; `state_counts` length = |S| |
| R5 | Snapshot Restore | Unchanged — restore reconstructs from DB |
| R6 | Fail-Fast on Corruption | Unchanged |
