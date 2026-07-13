# Tasks: Fase 5 — Paper Trading (Operational Phase)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~460 (6 files: 5 create + 1 modify) |
| 400-line budget risk | High (~460 > 400) |
| Chained PRs recommended | Yes |
| Suggested split | PR1 ~151L (models+contracts) → PR2 ~310L (session+bundler+CLI+tests) |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Base | Lines | Notes |
|------|------|-----------|------|-------|-------|
| 1 | Foundation — models, contracts, __init__ | PR 1 | main | ~151 | Pure types + validators, no external deps |
| 2 | Implementation — session, bundler, CLI, all tests | PR 2 | main | ~310 | Depends on PR1 merged; includes integration tests |

---

## Phase 1 — Foundation (PR 1)

- [x] T-001 `paper_trading/models.py` — 4 dataclasses (SessionReport, SessionManifest, ContractViolation) + SessionState StrEnum (~50L) → deps: none | verify: `pytest tests/unit/test_paper_trading_models.py -v` | REQ-PT-001
- [x] T-002 `paper_trading/contracts.py` — 6 validator fns: DRY_RUN_ENFORCED, NO_REAL_FUNDS, TEMPORAL_INTEGRITY, EVIDENCE_COMPLETENESS, DETERMINISTIC_REPRODUCIBILITY, REFLECTION_ISOLATION (~100L) → deps: T-001 | verify: `pytest tests/unit/test_paper_trading_contracts.py -v` | REQ-PT-002
- [x] T-003 `paper_trading/__init__.py` — re-export public API (~1L) → deps: T-001, T-002 | verify: `python -c 'from trady_ai.paper_trading import SessionReport, ContractViolation, SessionState'` | REQ-PT-001

## Phase 2 — Core Implementation (PR 2)

- [ ] T-004 `paper_trading/session.py` — PaperTradingSession with 7-state machine (PRE_FLIGHT→...→COMPLETE/ERROR), reconstruction, interactive blocking (~140L) → deps: T-001, T-002, ReflectionEngine, ExecutionEngine, EventCapture | verify: `pytest tests/integration/test_paper_trading_session.py::TestPaperTradingSession::test_s1_full_session -v` | REQ-PT-001, REQ-PT-004, REQ-PT-007
- [ ] T-005 `paper_trading/bundler.py` — EvidenceBundler.bundle(report) + regenerate_bundle(day, domain), SHA-256 manifest + contracts.json + session_report.json (~120L) → deps: T-001, T-004 report output | verify: `pytest tests/unit/test_paper_trading_bundler.py -v` | REQ-PT-005
- [ ] T-006 `cli/main.py` — Add `paper-trade` Click group + 3 commands: `session` (scope, domain, markets, non-interactive), `status` (day N/30), `bundle --day N` (~+50L) → deps: T-004, T-005 | verify: `pytest tests/unit/test_cli.py::TestPaperTradeCLI -v` | REQ-PT-006

## Phase 3 — Testing

- [x] T-007 Unit: `tests/unit/test_paper_trading_models.py` — dataclass construction, StrEnum values, defaults (~30L) → deps: T-001 | verify: `pytest tests/unit/test_paper_trading_models.py -v` | REQ-PT-001
- [x] T-008 Unit: `tests/unit/test_paper_trading_contracts.py` — S2 (dry_run fail), S3 (DB err), S6 (dup), S7 (evidence gap) (~60L) → deps: T-002 | verify: `pytest tests/unit/test_paper_trading_contracts.py -v` | REQ-PT-002
- [ ] T-009 Unit: `tests/unit/test_paper_trading_bundler.py` — bundle() output structure, regenerate_bundle() determinism, edge cases (~40L) → deps: T-005 | verify: `pytest tests/unit/test_paper_trading_bundler.py -v` | REQ-PT-005
- [ ] T-010 Integration: `tests/integration/test_paper_trading_session.py` — S1 full session mock, S4 (capture fail), S5 (engine error), S2/S3/S6/S7 error paths, S12 30-day gate (~100L) → deps: T-004 | verify: `pytest tests/integration/test_paper_trading_session.py -v` | REQ-PT-001, REQ-PT-007, REQ-PT-008
- [ ] T-011 CLI: Extend `tests/unit/test_cli.py` with TestPaperTradeCLI — S8 non-interactive exit codes, S9 status, S10 (bundle complete), S11 (bundle incomplete) (~50L) → deps: T-006 | verify: `pytest tests/unit/test_cli.py::TestPaperTradeCLI -v` | REQ-PT-006

## Implementation Order

1. **PR 1** — T-001 → T-002 → T-003 → T-007 → T-008 (foundation + tests, merge to main)
2. **PR 2** — T-004 → T-005 → T-006 → T-009 → T-010 → T-011 (core + tests, merge to main after PR1)

All 11 tasks are in order. No blockers. All 12 spec scenarios (S1–S12) are covered across the task verifications.
