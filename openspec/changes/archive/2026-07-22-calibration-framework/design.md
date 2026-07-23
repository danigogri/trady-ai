# Design: Calibration Framework

## 1. Component Architecture

```
                          ┌─ Phase A ─┐               ┌───── Phase B ─────┐
MarketInput │──→ Engine ──→ event_store │               │ ReflectionEngine    │
            │  (core/)      │                                         │
            │               │                                         ├─ calibr analyzer
            │ state_tracker │                                         │
            │    → StateGenerator.classify()                          │
            │    [N×N engine]                   calibrate review ─→ CLI ─→ Human
            │                                         │                   │
            │               │                         │                   │ calibrate adopt
            │               │                         ▼                   │ (sole write)
            └───────────────┘               EvidenceReport          calibration_adoptions
                                            (JSON, deterministic)    (append-only, provenance)
```

**Data flow**: MarketInput → StateGenerator.classify() → state_index → MarkovEngine N×N transition → snapshots → DB. CalibrationAnalyzer reads snapshots → computes AIC/BIC/χ²/entropy → EvidenceReport. CLI `calibrate review` reads report; `calibrate adopt` writes to `calibration_adoptions`.

## 2. StateGenerator ABC

**DESIGN CONSTRAINT** — specs R1, R2, R3 mandate the interface.

```python
# Location: src/trady_ai/strategies/markov/state_generator.py
class StateGenerator(ABC):
    @abstractmethod
    def classify(self, input: MarketInput) -> int: ...   # → [0, |S|-1]
    @property
    @abstractmethod
    def state_count(self) -> int: ...                     # |S|, immutable
    @property
    @abstractmethod
    def state_labels(self) -> list[str]: ...              # index i ↔ labels[i]
```

**DirectionalStateGenerator** (default |S|=3):
- Wraps current `MarketStateTracker.update()` threshold logic (price change %).
- Hardcodes labels `["UP", "DOWN", "NEUTRAL"]` — **DESIGN CHOICE**: embed DirectionalStateGenerator constants rather than a separate mapping layer.
- `classify()` produces identical indices to the existing `STATE_INDEX` → guarantees zero assertion changes for `DirectionalPersistence` (spec R2 scenario).

**VolatilityStateGenerator** (default |S|=3):
- Wraps `VolatilityPersistence._classify_volatility()` logic.
- Labels: `["HIGH", "LOW", "STABLE"]`.

**Registration**: module-level `_STATE_GENERATORS: dict[str, type[StateGenerator]]` mapping name → class. `get_generator(name) -> StateGenerator` factory. **DESIGN CHOICE**: simple dict registry over plugin discovery — sufficient for Phase B's two variants, extensible later.

**Relationship to StrategyBase**: orthogonal. `StateGenerator` produces state indices; `StrategyBase` consumes `MarketState`. They share nothing.

## 3. N-State Markov Engine Refactor

**DESIGN CONSTRAINT** — spec ADDED requirements: `state_space_size` at construction.

**Changes to `persistence.py`**:

| What | Before | After |
|------|--------|-------|
| L21-29 | Module-level `STATE_INDEX`, `INDEX_STATE`, `DIRECTION_MAP` dicts | **Deleted**. Moved to `DirectionalStateGenerator`. |
| L27-29 | Module-level `VOLATILITY_INDEX`, `VOLATILITY_INDEX_STATE`, `VOLATILITY_DIR_MAP` | **Deleted**. Moved to `VolatilityStateGenerator`. |
| L41 `__init__` | `(warmup_ticks, threshold_pct)` | Add `state_generator: StateGenerator \| None = None`. Default: `DirectionalStateGenerator(state_space_size=3)`. |
| L42-43 `_transition_counts` | `np.zeros((3,3))` | `np.zeros((|S|,|S|))` from `state_generator.state_count`. |
| L43 `_state_counts` | `np.zeros(3)` | `np.zeros(|S|)`. |
| L72 `on_update` | `current_idx = STATE_INDEX[state.state]` | `current_idx = self._generator.classify(input)`. Engine no longer reads `state.state` — it calls `classify()`. |
| L82-113 `on_evaluate` | `STATE_INDEX`, `INDEX_STATE`, `DIRECTION_MAP` lookups | Uses `self._generator.state_labels[best_idx]` + internal direction map. |
| L152-193 `restore()` | `cls(warmup_ticks, threshold_pct)` | `cls(warmup_ticks, threshold_pct, state_generator=generator)`. Reads `state_space_size` from snapshot. |

**VolatilityPersistence override**: `on_update(L267)` replaces `VOLATILITY_INDEX[vol_state]` with `self._generator.classify(...)`.

**Backward compatibility**: `DirectionalPersistence` constructed with default `DirectionalStateGenerator(3)` produces identical signals. **Spec prescribes zero assertion changes** — the adapter pattern ensures this.

**`MarketState.state` type**: relaxed from `Literal["UP", "DOWN", "NEUTRAL"]` to `str` (R1 — domain-agnostic). Existing generators still produce these strings; new generators may produce arbitrary labels.

## 4. DB Schema Changes

| Table | Change | Rationale |
|-------|--------|-----------|
| `market_states` | `state` CHECK relaxed: `state IN ('UP','DOWN','NEUTRAL')` → `CHECK(LENGTH(state) <= 64)` | N-state engines produce arbitrary labels (spec R1). 64-char cap is safety, not semantics. |
| `strategy_snapshots` | ADD `state_space_size INTEGER NOT NULL DEFAULT 3`, `state_generator TEXT NOT NULL DEFAULT 'directional'` | Snapshot must record |S| for restore. Additive — no migration needed. |
| NEW `calibration_adoptions` | `id PK, domain, strategy_name, states INT, generator TEXT, evidence_report_ref TEXT, operator TEXT, adopted_at TEXT, reason TEXT` | Governance spec R3. Append-only — no UPDATE/DELETE triggers. |
| `reflection_config` | New keys: `adopted_states_{strategy}`, `adopted_generator_{strategy}`, `review_threshold_days` | Governance spec R5. Existing table, additive. |

**Migration**: Phase A script relaxes CHECK with ALTER TABLE (SQLite 3.35+). Phase B creates `calibration_adoptions` via `init_reflection_tables()`. All additive — zero data migration.

## 5. Evidence Pipeline (`reflection/calibration/`)

**Module structure**:

```
reflection/calibration/
    __init__.py
    analyzer.py      # CalibrationAnalyzer (matches DriftAnalyzer pattern)
    metrics.py       # aic(), bic(), markov_chi2(), persistence(), conditional_entropy()
    models.py        # EvidenceReport dataclass
    persistence.py   # save_evidence_report(), load_transition_counts()
```

**CalibrationAnalyzer** — **DESIGN CHOICE**: stateless, matches existing `DriftAnalyzer` injection pattern:

```python
class CalibrationAnalyzer:
    def analyze(self, db, domain, strategy_name) -> EvidenceReport:
        # 1. Load transition_counts + state_sequence from strategy_snapshots
        # 2. Compute P from MLE: p_ij = n_ij / Σ_j n_ij
        # 3. Compute each metric (pure functions, no side effects)
        # 4. Return EvidenceReport
```

**Metrics** (all in `metrics.py` as pure functions — **DESIGN CHOICE**: testable in isolation):

| Function | Formula | Output |
|----------|---------|--------|
| `aic(trans, seq)` | -2 ln(L) + 2k, k=|S|(|S|-1) | float |
| `bic(trans, seq, n)` | -2 ln(L) + k ln(n) | float |
| `markov_chi2(seq, S)` | Σᵢⱼ (nᵢⱼ - eᵢⱼ)² / eᵢⱼ | dict{statistic, p_value, df, reject_null} |
| `state_persistence(P)` | 1/(1-pᵢᵢ) per state | dict[int→float] |
| `conditional_entropy(P, pi)` | -Σᵢ πᵢ Σⱼ pᵢⱼ log₂ pᵢⱼ | float |

**Determinism**: closed-form MLE, scipy chi2.sf for p-value (deterministic), fixed np.float64 arithmetic. No random seeds. **Spec requires byte-identical JSON** → `sort_keys=True`, float precision via `repr()`.

**ReflectionEngine integration**: add optional `calibration_analyzer` to ctor (spec MODIFIED requirement). When present, `reflect()` calls `analyze()` after drift step → appends `evidence_report` to `ReflectionReport` data.

## 6. CLI Commands

**DESIGN CHOICE**: new `calibrate` Click group (separate from `reflect` to enforce governance boundary).

```bash
trady-ai calibrate review --domain PM-5M [--strategy directional_persistence]
  # Output: plain-text AIC/BIC/χ²/persistence/entropy. Exit 0.
  # Reads: strategy_snapshots via CalibrationAnalyzer.

trady-ai calibrate adopt --domain PM-5M --states 4 --generator volatility [--confirm]
  # Without --confirm: displays summary, exit 1. With --confirm: persists to calibration_adoptions, writes cal-NNN bundle. Exit 0.
  # Validates: |S|≥2, generator name exists, evidence report ref valid.
```

**Implementation**: adds `calibrate` group to `cli.main` (L224+ area, alongside `paper_trade`). Error handling: Click's `raise SystemExit(1)` for validation failures. Plain text only — no interactive prompts (spec R1).

## 7. Governance Boundary

**Enforcement design**:

1. `CalibrationAnalyzer` is stateless and read-only — it queries DB, computes metrics, returns `EvidenceReport`. **No write path**.
2. `calibrate adopt` is the **sole function that writes** `calibration_adoptions`. `_build_reflection_engine()` never injects a calibration analyzer into `reflect()` (read-only).
3. `calibration_adoptions` table has no UPDATE/DELETE code paths — only INSERT. **DESIGN CHOICE**: no triggers — app-level enforcement via code review.
4. Provenance: `operator` = `$USER@$HOSTNAME`, `evidence_report_ref` = report SHA-256, `adopted_at` = ISO-8601, `reason` = human-supplied text.
5. Review window: `_check_calibration_readiness()` in `ReflectionEngine` already exists (L157-206). Extended to read `review_threshold_days` from `reflection_config`.

## 8. File Manifest

**Phase A (create)**:
- `src/trady_ai/strategies/markov/state_generator.py` — StateGenerator ABC + DirectionalStateGenerator + VolatilityStateGenerator

**Phase A (modify)**:
- `src/trady_ai/strategies/markov/persistence.py` — remove module dicts, inject StateGenerator, N×N arrays
- `src/trady_ai/strategies/markov/__init__.py` — export StateGenerator classes
- `src/trady_ai/core/models.py` — MarketState.state: `Literal[...]` → `str`
- `src/trady_ai/core/persistence.py` — relax market_states CHECK, add snapshot columns
- `src/trady_ai/core/markov_strategy.py` — pass StateGenerator to engine if needed

**Phase B (create)**:
- `src/trady_ai/reflection/calibration/__init__.py`
- `src/trady_ai/reflection/calibration/analyzer.py`
- `src/trady_ai/reflection/calibration/metrics.py`
- `src/trady_ai/reflection/calibration/models.py`
- `src/trady_ai/reflection/calibration/persistence.py`

**Phase B (modify)**:
- `src/trady_ai/reflection/engine.py` — optional `calibration_analyzer` in ctor, call in `reflect()`
- `src/trady_ai/reflection/models.py` — add `evidence_report` to `ReflectionReport`
- `src/trady_ai/cli/main.py` — add `calibrate` group + `review`/`adopt` commands
- `src/trady_ai/core/persistence.py` — add `calibration_adoptions` table to `init_reflection_tables()`

## 9. Sequence Diagrams

**Session execution with injected StateGenerator (Phase A)**:
```
MarketInput ─→ Engine.run()
                  │
                  ├→ state_tracker.update(MarketInput) → MarketState (for persistence only)
                  ├→ strategy.update(state) 
                  │     └→ self._generator.classify(MarketInput) → index
                  │     └→ _transition_counts[prev][curr] += 1
                  ├→ signal = strategy.evaluate(state)
                  │     └→ row = _transition_counts[curr_idx]
                  │     └→ argmax → best_idx → labels[best_idx]
                  └→ persist
```

**Calibration review → adoption (Phase B)**:
```
Human: calibrate review --domain PM-5M
  → CLI reads strategy_snapshots
  → CalibrationAnalyzer.analyze() → EvidenceReport
  → Displays AIC=245.3 BIC=310.7 χ² p=0.001 entropy=1.2
  → Exit 0

Human evaluates evidence (offline, review window)

Human: calibrate adopt --domain PM-5M --states 4 --generator volatility --confirm
  → Validates |S|≥2, generator="volatility" exists
  → Writes calibration_adoptions row (append-only)
  → Writes cal-NNN bundle (evidence_report.json, adopted_config.json, provenance.json)
  → Exit 0
  ── GOVERNANCE BOUNDARY ──
  → Next engine session reads adopted config from reflection_config
  → Engine constructed with VolatilityStateGenerator(|S|=4)
```

## 10. Risk Mitigations

| Risk | Mitigation in Design |
|------|---------------------|
| Engine refactor breaks existing tests | Adapter pattern: `DirectionalStateGenerator(3)` wraps current logic identically. `classify()` mirrors the old `STATE_INDEX`. No assertion changes. |
| CHECK constraint migration loses data | New CHECK (`LENGTH(state) <= 64`) is less restrictive than old — all existing rows pass. ALTER TABLE is idempotent. |
| AIC/BIC misuse | `metrics.py` functions reference scipy.stats implementations. Synthetic P-matrix tests planned (known-answer tests). `np.linalg.slogdet` for near-singular matrices. |
| Governance boundary blur | `CalibrationAnalyzer` is stateless and read-only. `calibrate adopt` is the sole INSERT path for `calibration_adoptions`. No UPDATE/DELETE code. |
