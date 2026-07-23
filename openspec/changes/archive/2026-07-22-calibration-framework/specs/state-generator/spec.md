# State Generator Specification

**Domain**: state-generator | **Type**: New | **RFC**: RFC-004 §Model-Agnostic Markov
**Research**: MARKOV-STATE-SPACE-METHODOLOGY-2026-07-23.md (§2.1–2.3)

## Purpose

Define the pluggable `StateGenerator` ABC for domain-agnostic state classification. The
engine operates on integer state indices only — state generators are the sole boundary
where semantic labels exist.

**Deterministic boundary**: `classify()` is deterministic. Intelligence (clustering, ML)
is a future alternate implementation path — no AI in this contract.

---

## Requirements

### R1: StateGenerator ABC

The system SHALL define `StateGenerator` as an ABC in `strategies/markov/state_generator.py`:

| Method | Returns | Contract |
|--------|---------|----------|
| `classify(input: MarketInput) → int` | index ∈ [0, \|S\|-1] | Deterministic; same input → same index |
| `state_count → int` | \|S\| | Fixed; MUST NOT change during lifetime |
| `state_labels → list[str]` | length = \|S\| | Human-readable; index i ↔ labels[i] |

#### Scenario: Deterministic classification

- GIVEN a DirectionalStateGenerator(|S|=3) and MarketInput(price=0.51, prev=0.50)
- WHEN `classify()` called twice with the same input
- THEN both calls return identical state_index

#### Scenario: Pluggability without engine changes

- GIVEN a registered StateGenerator with |S|=5
- WHEN MarkovEngine is constructed with that generator
- THEN engine operates on 5×5 matrix with zero engine code changes

### R2: DirectionalStateGenerator — Backward Compat

`DirectionalStateGenerator` SHALL be the default implementation:
- Preserves the existing `MarketStateTracker` threshold-based UP/DOWN/NEUTRAL logic
- `classify()` MUST produce identical indices to current `MarketStateTracker.update()` state labels mapped via the existing `STATE_INDEX` dict
- Default |S| = 3

#### Scenario: Identical output to pre-refactor engine

- GIVEN 100 MarketInput ticks processed by current 3-state tracker
- WHEN same ticks processed by DirectionalStateGenerator(|S|=3)
- THEN state index sequence maps to identical state labels as before

### R3: State Index Determinism

`classify()` MUST be a pure function: same `MarketInput` + same generator state → same
`int`. Generators MUST NOT use time-of-day, random seeds, or external state.

#### Scenario: Same input across processes

- GIVEN MarketInput with identical fields
- WHEN classify() called from two different Python processes
- THEN both return the same state_index
