# PR: feat: archive measurement-calibration

**Commit**: 4cf223f
**SDD Cycle**: proposal → specs (14 REQs, 5 domains) → design → tasks (20) → apply (13/13, 3 PRs stacked-to-main) → verify (35/48 compliant, 7 PARTIAL) → archive

## What was built

| Component | Status |
|-----------|--------|
| ATRCalculator | Deterministic, 100% coverage |
| MarketStateTracker ATR integration | Backward compatible, dormant |
| ExecutionResult.strategy_snapshot | Strategy→Reflection handoff |
| ReflectionEngine.persist_snapshot() | Snapshots with created_by provenance |
| Schema: created_by column | Additive, no breaking changes |
| Architecture Contract D-003 | §29 documented deviation |
| strategy_snapshot.json in bundle | SHA-256 checksummed |

## What is NOT activated

⚠️ **ATR path is DORMANT.** engine.py still uses threshold_pct=0.001 for the running experiment. The operator must run pre-Day-0 calibration to determine optimal α and N, then explicitly adopt and activate.

## Discovery Phase (pre-SDD)

5 research documents produced and archived:
- STATUS-REPORT-2026-07-29.md — 55 sessions, Day 2, experiment state
- ARCHITECTURAL-REVIEW-2026-07-29.md — adversarial analysis, Option D
- RESEARCH-REPORT-2026-07-29.md — scientific evidence, ATR methodology
- DISCOVERY-REPORT-2026-07-29.md — conceptual reframe: threshold = measurement
- CLOSURE-REPORT-2026-07-29.md — GO WITH CONDITIONS, SDD authorized

## Verify Findings (7 PARTIAL → backlog BL-034..040)

All PARTIAL scenarios are test coverage gaps, not implementation defects. Registered for traceability.

## Test Results

- 712+ tests passing
- mypy strict: clean (11 changed files)
- ruff: clean
- 0 regressions

## Merge Strategy

Stacked-to-main: 3 conceptual PRs merged sequentially. Code deployed directly to main via SDD archive squash (SDD-CYCLE-GOVERNANCE §5).
