# Markov Persistence Engine Specification

**Domain**: markov-persistence-engine | **Type**: New | **RFC**: RFC-003 §Initial Strategy Focus, §Statistical Traceability
**Package**: `src/trady_ai/strategies/markov/`

## Purpose

SQLite-persisted 3×3 Markov transition matrix strategy. Computes state-transition probabilities, generates deterministic signals via `argmax`, persists snapshots for audit. Migrates `core/markov_strategy.py` → `strategies/markov/persistence.py`.

---

## Requirements

### R1: V1 Markov Variants

Two V1 variants (RFC-003 §Initial Strategy Focus):

| Variant | State Space | Matrix | Output |
|---------|-------------|--------|--------|
| DirectionalPersistence | UP/DOWN/NEUTRAL | 3×3 int64 counts | direction ∈ {LONG, SHORT, NEUTRAL} |
| VolatilityPersistence | HIGH/LOW/STABLE | 3×3 int64 counts | confidence adjustment factor |

Both: `numpy.int64` counters, `np.argmax` (first-index tie-break), `warmup_ticks`/`is_ready()` preserved. Variants are INDEPENDENT — no cross-variant coupling. Continuation probabilities and state-transition probabilities are DERIVED METRICS from the matrix, not separate classes.

**Scenario: DirectionalPersistence matches Fase 2**
- GIVEN same 100 MarketState inputs
- WHEN DirectionalPersistence and legacy MarkovStrategy both process them
- THEN identical Signal outputs (field-by-field)

**Scenario: VolatilityPersistence classifies states**
- GIVEN MarketState with increasing price range
- WHEN `update(state)` called
- THEN internal volatility state transitions to HIGH if range exceeds threshold

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
