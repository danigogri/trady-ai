# Tasks: Calibration Framework

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Work Units

| Unit | PR | Focused test | Harness | Rollback |
|------|----|-------------|---------|----------|
| 1 — Foundation | PR 1 | `pytest tests/unit/strategies/markov/ tests/unit/test_state.py` | `trady-ai backtest --input data.csv` (same output) | Revert state_generator.py + restore 3×3 dicts |
| 2 — Evidence | PR 2 | `pytest tests/unit/test_calibration_analyzer.py` | `trady-ai calibrate review --domain PM-5M` | Delete reflection/calibration/ dir |

## Phase A: Foundation (spec: state-generator, markov-engine MODIFIED/PRIOR)

- [x] A.1 Create `strategies/markov/state_generator.py`: `StateGenerator` ABC (`classify→int`, `state_count`, `state_labels`) + `DirectionalStateGenerator` wrapping threshold logic (|S|=3) + `VolatilityStateGenerator` wrapping _classify_volatility (|S|=3) + `get_generator()` factory (spec R1, R2, R3)
- [x] A.2 Embed `STATE_INDEX`/`INDEX_STATE`/`DIRECTION_MAP` inside `DirectionalStateGenerator`; `VOLATILITY_*` dicts inside `VolatilityStateGenerator`; module-level dicts preserved for backward compat imports
- [x] A.3 Refactor `MarkovPersistenceEngine.__init__`: accept `state_generator` param (default `DirectionalStateGenerator(3)`); `np.zeros((|S|,|S|))` from generator (spec: N-State Matrix)
- [x] A.4 Refactor `on_update()`: replace `STATE_INDEX[state.state]` with `self._generator.classify_from_label(state.state)`; engine uses abstract indices only (spec: Abstract Indices)
- [x] A.5 Refactor `on_evaluate()`: use `self._generator.state_labels[best_idx]` + `self._generator.signal_for_state(best_idx)` instead of `INDEX_STATE`/`DIRECTION_MAP`
- [x] A.6 Refactor `VolatilityPersistence.on_update()` + `on_evaluate()`: replace `VOLATILITY_INDEX[vol_state]` with `self._generator.classify_from_label(vol_state)` (spec MODIFIED R1)
- [x] A.7 Relax `market_states.state` CHECK: `IN ('UP','DOWN','NEUTRAL')` → `LENGTH(state) <= 64` in core/persistence.py (design §4)
- [x] A.8 Add `state_space_size INTEGER DEFAULT 3`, `state_generator TEXT DEFAULT 'directional'` to `strategy_snapshots` in `init_strategy_tables()`
- [x] A.9 Change `MarketState.state`: `Literal["UP","DOWN","NEUTRAL"]` → `str` in core/models.py
- [x] A.10 Update `on_snapshot()` + `persist_strategy_snapshot()`: include `state_space_size`, `state_generator` name
- [x] A.11 Export new classes + factory from `strategies/markov/__init__.py`
- [x] A.12 RED: Verify `DirectionalPersistence`/`VolatilityPersistence` produce identical signals on 100-tick backtest (`pytest tests/unit/strategies/markov/ tests/unit/test_state.py tests/unit/test_markov_strategy.py` — zero assertion changes)

## Phase B: Evidence Pipeline (spec: evidence-pipeline, governance, calibration-bundles ADDED)

- [x] B.1 Create `reflection/calibration/` module: `__init__.py` + `metrics.py` pure functions (`aic`, `bic`, `markov_chi2`, `state_persistence`, `conditional_entropy`) — all deterministic (spec: AIC/BIC/χ²/persistence/entropy)
- [x] B.2 RED+GRN: Write `tests/unit/test_calibration_metrics.py` — known-answer tests on synthetic matrices (uniform, deterministic, mixed)
- [x] B.3 Create `models.py`: `EvidenceReport` dataclass (aic, bic, markov_test dict, persistence dict, entropy, computed_at) + `AdoptedStateSpace`
- [x] B.4 Create `analyzer.py`: `CalibrationAnalyzer` stateless class matching `DriftAnalyzer` pattern; `analyze(db, domain, strategy_name) → EvidenceReport`
- [x] B.5 Create `persistence.py`: `save_evidence_report()`, `load_transition_counts()`, `save_adoption()`, `init_calibration_tables()`
- [x] B.6 Add optional `calibration_analyzer` to `ReflectionEngine.__init__()` (spec MODIFIED: Engine Orchestration)
- [x] B.7 Add `evidence_report` field to `ReflectionReport` dataclass in reflection/models.py
- [x] B.8 Call `calibration_analyzer.analyze()` in `reflect()` after drift step; append evidence_report to report
- [x] B.9 Extend `_check_calibration_readiness()` to read `review_threshold_days` from `reflection_config` (governance R5)
- [x] B.10 Add `calibrate` Click group to `cli/main.py`; implement `calibrate review --domain --strategy` → plain text AIC/BIC/χ²/entropy (governance R1)
- [x] B.11 Implement `calibrate adopt --domain --states --generator [--confirm]`: validate |S|≥2, generator exists; `--confirm` gates write; exit 1 without it (governance R2/R4)
- [x] B.12 Add `calibration_adoptions` table to `init_reflection_tables()`: id PK, domain, strategy_name, states, generator, evidence_report_ref, operator, adopted_at, reason (governance R3)
- [x] B.13 Extend `EvidenceBundler` in paper_trading/bundler.py: `calibration_bundle()` → `cal-NNN/` dir with evidence_report.json, adopted_config.json, provenance.json, manifest.json (spec: Calibration Bundles)
- [x] B.14 Wire `calibrate adopt` to call `calibration_bundle()` after adoption write; store `adopted_states_{s}` / `adopted_generator_{s}` in `reflection_config`
- [x] B.15 RED+GRN: Write `tests/unit/test_calibration_analyzer.py` — inject synthetic snapshots, verify EvidenceReport
- [x] B.16 RED+GRN: Write `tests/unit/test_calibration_cli.py` — review exit 0, adopt exit 1 without --confirm, exit 0 with
- [x] B.17 RED+GRN: Write `tests/unit/test_calibration_bundler.py` — verify cal-NNN output, manifest SHA-256, regenerability
- [x] B.18 Run full suite: `pytest --cov=trady_ai` ≥ 80% (new code 93%+), `ruff check` + `mypy src/trady_ai/reflection/calibration/` clean
