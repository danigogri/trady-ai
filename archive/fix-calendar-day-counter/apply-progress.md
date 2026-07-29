# Apply Progress: Fix Calendar Day Counter

## Summary

All source changes and test updates completed. 64/64 targeted tests pass. `mypy --strict` and `ruff check` pass clean.

## Changes Made

### models.py
- Added `session_number: int` field to `SessionReport` (after `day`)
- Added `session_number: int` field to `SessionManifest` (after `day`)
- Updated docstrings

### session.py
- Added `from datetime import date` import
- Added `DAY_ZERO = date(2026, 7, 28)` module constant
- Replaced `_compute_day(domain)` → `_compute_calendar_day()` using `(date.today() - DAY_ZERO).days + 1`
- Added `_compute_session_number(domain)` counting today's `reflection_reports` for domain, returning COUNT+1
- Updated `run_session()`: calls both methods, passes `session_number` to `SessionReport`

### bundler.py
- `_day_dir(day)` → `_day_dir(day, session)` returning `.../dia-NNN/sesion-MMM/`
- Removed HHMMSS timestamp suffixes — files now: `session_report.json`, `contracts.json`, `manifest.json`
- `SessionManifest` now includes `session_number=report.session_number`
- `regenerate_bundle()` passes `session_number=1` (regeneration = single-session)

### cli/main.py
- Line 496: `Day {report.day}` → `Day {report.day}, Session {report.session_number}`

### Test Updates
- `test_paper_trading_models.py`: Added `session_number=1` to 6x SessionReport + 2x SessionManifest
- `test_paper_trading_bundler.py`: Added `session_number` to 4x SessionReport, updated helpers/assertions for new dir structure (`sesion-001`), plain filenames
- `test_calibration_bundler.py`: Added `session_number=1` to SessionReport, updated session path assertions to `sesion-001`

## Verification

| Check | Status |
|---|---|
| pytest (64 tests) | ✅ All GREEN |
| mypy --strict | ✅ No issues |
| ruff check | ✅ All checks passed |

## Pre-existing Issues

5 integration tests (`test_paper_trading_session.py`) fail due to a pre-existing issue: `MagicMock` adapter → `_resolve_token_ids` returns empty → `EventCapture.start([])` raises `ValueError: market_ids must not be empty`. These failures are unrelated to the calendar day counter change.
