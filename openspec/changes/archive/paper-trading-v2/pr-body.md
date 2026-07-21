# Paper Trading v2 — 4-Clock Event-Centric Architecture

## What Changed

Transitioned the Paper Trading subsystem from a **session-centric 7-stage state machine** (daily cadence) to a **4-clock unidirectional event-centric flow** (15-min cadence, sub-daily reconstruction). This aligns implementation with the frozen Paper Trading Architecture Contract v1.0.

## Why

Fase 5's session-centric model coupled Evidence, Decision, and Reflection together, blocking independent clock frequencies and sub-daily reconstruction. The 4-clock architecture decouples these concerns:

- **Discovery Clock** → Pre-session guard script ensures deterministic market rotation
- **Evidence Clock** → Tracks progress via `MAX(seq)` from event store (not calendar dates)
- **Decision Clock** → Tracks via `last_processed_seq` from execution log
- **Reflection Clock** → Tracks via `last_report_date` from reflection reports

Each clock tracks its own progress independently, enabling per-sequence reconstruction and 15-min execution rhythm without reprocessing the same events.

## Affected Files

| File | Action | Description |
|------|--------|-------------|
| `scripts/ensure_active_market.py` | **New** | Discovery Clock guard — stateless, first-valid, deterministic market selection |
| `src/trady_ai/paper_trading/session.py` | **Modified** | Per-clock reconstruction: `_reconstruct_stages()` uses seq-based tracking instead of calendar dates |
| `src/trady_ai/paper_trading/models.py` | **Modified** | `SessionReport.market_ids: list[str]` for operator audit traceability |
| `src/trady_ai/paper_trading/contracts.py` | **Modified** | `TEMPORAL_INTEGRITY` refined from per-day to per-sequence-overlap check |
| `src/trady_ai/paper_trading/bundler.py` | **Modified** | Concurrent-write protection: HHMMSS timestamp suffixes in filenames |
| `src/trady_ai/cli/main.py` | **Modified** | `--duration` flag for timed capture; `market_ids` in CLI output |
| `src/trady_ai/core/persistence.py` | **Modified** | Supporting persistence changes |
| `src/trady_ai/config/settings.py` | **Modified** | `TRADY_AI_ACTIVE_MARKETS` env var read for guard script coordination |
| `tests/paper_trading/test_guard.py` | **New** | 4 scenarios: all active, rotation, no candidates, env mutation |
| `tests/paper_trading/test_reconstruction.py` | **New** | 5 scenarios: per-clock resume from any interruption point |
| `tests/paper_trading/test_subdaily_execution.py` | **New** | 6 scenarios: 15-min rhythm, duration, concurrent bundles, market_ids |
| `tests/unit/test_paper_trading_contracts.py` | **Modified** | 26+ contract tests updated for per-seq TEMPORAL_INTEGRITY |
| `tests/unit/test_paper_trading_bundler.py` | **Modified** | 8 tests updated for HHMMSS naming |
| `tests/integration/test_paper_trading_session.py` | **Modified** | 12 integration tests for full session lifecycle |

## Test Results

- **pytest**: ✅ 456 passed, 0 failed, 0 skipped (29.09s)
- **mypy strict**: ✅ 0 errors in 47 source files
- **coverage**: ✅ 91% (threshold: 90%)
- **ruff**: ⚠️ 23 style-only lint warnings (all auto-fixable, no logic issues)

## Spec Compliance

- **14/14 requirements** compliant (6 ADDED, 6 MODIFIED, 2 PRESERVED)
- **23/23 scenarios** compliant
- **4/4 architectural contracts** verified (AC-3 Clock Isolation, AC-4 Reconstruction, TEMPORAL_INTEGRITY, Bundler)

## Verdict

**PASS WITH WARNINGS** — All requirements implemented, all tests pass, all architectural contracts verified. 23 lint warnings (style only) deferred.

## Deferred Items

The following findings are recorded as operational backlog entries per Contract §20.4 (Backlog Protocol):

| ID | Description | Priority |
|----|-------------|----------|
| BL-024 | Ruff import sorting (I001) — 7 errors, auto-fixable | Low |
| BL-025 | Ruff unused imports (F401) — 6 errors, auto-fixable | Low |
| BL-026 | Ruff variable naming (N806) — 10 errors, in test files | Low |
