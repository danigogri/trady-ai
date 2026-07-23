# Markov Persistence Engine Specification

**Domain**: markov-persistence-engine | **Type**: New (with Calibration Framework modifications) | **RFC**: RFC-003 §Initial Strategy Focus, §Statistical Traceability, RFC-004
**Package**: `src/trady_ai/strategies/markov/`

## Purpose

SQLite-persisted N×N Markov transition matrix strategy. Computes state-transition probabilities, generates deterministic signals via `argmax`, persists snapshots for audit. Supports N-state matrices via pluggable `StateGenerator` ABC.

---

## Requirements

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

### Requirement: R1 — V1 Markov Variants (MODIFIED)

DirectionalPersistence and VolatilityPersistence SHALL delegate state classification to
their configured `StateGenerator` implementation instead of hardcoding `STATE_INDEX` and
`VOLATILITY_INDEX` dicts. The internal mapping dicts move into `DirectionalStateGenerator`
and `VolatilityStateGenerator` respectively.

(Previously: hardcoded module-level `STATE_INDEX`, `VOLATILITY_INDEX`, `DIRECTION_MAP`, `VOLATILITY_DIR_MAP` dicts)

| Variant | Default Generator | \|S\| |
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

### R2: Signal Generation Contract

Per RFC-003 §Signal Philosophy — signals are deterministic outputs, NOT commands:
- `direction`: mapped from argmax next state (UP→LONG, DOWN→SHORT, NEUTRAL→NEUTRAL)
- `confidence`: `max(probs)` — transition probability of chosen direction
- `metadata`: MUST include `{"probabilities": probs.tolist()}`
- `id`: UUID5 from `f"{name}:{market_id}:{timestamp.isoformat()}"`
- Not ready → Signal(NEUTRAL, 0.0, {"reason": "warmup"})
- Zero-transition row → Signal(NEUTRAL, 0.0, {"reason": "no_transitions_from_current_state"})

**Scenario: evaluate after warmup**
- GIVEN warmup_ticks=50, 60 obs processed, state="UP"
- WHEN `evaluate(state)` called
- THEN Signal with direction=argmax(UP row), confidence=max(prob), metadata has probabilities

**Scenario: zero-transition row**
- GIVEN state="NEUTRAL" with zero outgoing transitions
- WHEN `evaluate(state)` called
- THEN Signal(NEUTRAL, 0.0, {"reason": "no_transitions_from_current_state"})

---

### R3: Internal Contracts Only

Per RFC-003 §Relationship With Deterministic Core — strategies consume ONLY normalized contracts:
- Input: `MarketState` (from `core.models`) — produced by `MarketStateTracker`, NOT adapters
- Flow: Platform → Adapter → MarketInput → MarketStateTracker → **MarketState** → Strategy
- Strategy MUST NOT import from `trady_ai.adapters` or access `sqlite_utils.Database` directly

**Scenario: strategy receives MarketState from engine**
- GIVEN engine pipeline processes a MarketInput
- WHEN strategy.update() called
- THEN argument is MarketState instance (not raw dict, not adapter payload)

---

### R4: Statistical Traceability — Parameter + Evaluation Lineage

Per RFC-003 §Statistical Traceability — preserve signal lineage, parameter lineage, evaluation lineage, replay capability.

`strategy_snapshots` table (append-only): strategy_name, domain, tick_number, transition_counts (JSON), state_counts (JSON), warmup_ticks, threshold_pct, snapshot_at. Persisted after each `update()`.

**Scenario: update persists snapshot**
- GIVEN 10 observations processed
- WHEN `update(state)` called (11th)
- THEN strategy_snapshots gains row with tick_number=11, updated counts

**Scenario: snapshots are append-only**
- GIVEN 50 rows for ("markov_persistence", "PM-5M")
- WHEN new update() occurs
- THEN row count = 51 — no UPDATE, no DELETE

---

### R5: Snapshot Restore

`restore(domain, name, db) -> MarkovPersistenceEngine`: loads latest snapshot, reconstructs transition_counts, state_counts, total_obs, last_state. Restored instance MUST produce identical outputs for same subsequent inputs.

**Scenario: restore produces identical results**
- GIVEN engine A processed 100 ticks, snapshot at tick=100
- WHEN engine B restored from that snapshot
- AND both process 10 more ticks
- THEN identical signals for all 10

**Scenario: restore from empty raises**
- GIVEN no snapshot for ("markov_persistence", "UNKNOWN")
- WHEN `restore()` called
- THEN raises `RuntimeError("No snapshot found")`

---

### R6: Fail-Fast on Corruption

Per RFC-003 §Failure Philosophy — no silent degradation, no hidden fallback:
- Corrupted snapshot (malformed JSON, wrong shape) → `ValueError`
- No silent re-initialization from empty matrix

**Scenario: corrupted snapshot raises**
- GIVEN row with malformed transition_counts JSON
- WHEN `restore()` loads it
- THEN raises `ValueError("Corrupted snapshot")` — does NOT fall back to empty matrix

---

## Determinism Guarantees

- Same counts + same state → same Signal (always)
- `np.argmax` tie-break: first index wins
- UUID5 deterministic: same inputs → same ID
- Counts stored as int64 TEXT in SQLite (no floating-point)
