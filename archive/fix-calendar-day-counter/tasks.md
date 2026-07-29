# Tasks: Fix Calendar Day Counter

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~76 (range 60–90) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Core — Day Counter & Models

- [x] 1.1 **session.py**: Add `DAY_ZERO = date(2026, 7, 28)` module constant, import `date` from `datetime`
- [x] 1.2 **session.py**: Replace `_compute_day()` with `_compute_calendar_day()` returning `(date.today() - DAY_ZERO).days + 1`
- [x] 1.3 **session.py**: Add `_compute_session_number(domain)` counting `reflection_reports` WHERE domain=? AND DATE(created_at)=DATE('now'), return COUNT+1
- [x] 1.4 **session.py**: In `run_session()`, call `_compute_calendar_day()` and `_compute_session_number(domain)`, pass `session_number` to `SessionReport`
- [x] 1.5 **models.py**: Add `session_number: int` field to `SessionReport` dataclass
- [x] 1.6 **models.py**: Add `session_number: int` field to `SessionManifest` dataclass

## Phase 2: Bundle Layout

- [x] 2.1 **bundler.py**: Add `_day_dir(day, session)` (renamed to take session param) returning `dia-{day:03d}/sesion-{session:03d}/`, use in `bundle()` instead of flat file writes
- [x] 2.2 **bundler.py**: Remove HHMMSS suffix from filenames — write `session_report.json`, `contracts.json`, `manifest.json` directly
- [x] 2.3 **bundler.py**: Update `SessionManifest` construction to include `session_number`
- [x] 2.4 **bundler.py**: Update `bundle()` return to session dir path, update `regenerate_bundle()` to pass `session_number=1` (regeneration is single-session)

## Phase 3: CLI Display

- [x] 3.1 **cli/main.py**: Update session output line 496 from `Day {report.day}` to `Day {report.day}, Session {report.session_number}`

## Phase 4: Tests — RED-first for new assertions

- [x] 4.1 **tests/unit/test_paper_trading_models.py**: Add `session_number=1` to all `SessionReport` and `SessionManifest` constructions
- [x] 4.2 **tests/unit/test_paper_trading_bundler.py**: Update all `SessionReport` and `SessionManifest` constructions with `session_number`, update `bundle_path.name` assertion from `"dia-005"` to `"sesion-001"`, change file globs from `-*.json` to plain `.json`
- [x] 4.3 **tests/paper_trading/test_subdaily_execution.py**: File does not exist in test tree — skipped
- [x] 4.4 **tests/integration/test_paper_trading_session.py**: No direct `SessionReport` constructions in file — no changes needed
- [x] 4.5 **verify**: Run `python -m pytest tests/unit/test_paper_trading_models.py tests/unit/test_paper_trading_bundler.py tests/unit/test_calibration_bundler.py tests/unit/test_cli.py -v` — 64/64 GREEN. Integration tests have 5 pre-existing failures unrelated to this change (MagicMock adapter → empty token_ids).
