# Proposal: Fix Calendar Day Counter

*Roadmap Phase: 5 (Paper Trading)*

## Intent

`_compute_day()` in `session.py` uses `COUNT(*) FROM reflection_reports` — it counts sessions, not calendar days. At 96 sessions/day, day 30 triggers in ~7.5 hours. REQ-PT-005 and REQ-PT-008 already mandate calendar-day semantics; the implementation was never updated for sub-daily execution.

## Scope

### In Scope
- Replace `_compute_day()` with `_compute_calendar_day()` (frozen DAY_ZERO date math)
- Add `_compute_session_number()` (DB count of today's sessions per domain)
- Change bundle layout: `dia-{day}/sesion-{session}/` (replaces HHMMSS suffix)
- Add `session_number: int` to `SessionReport` model
- Update CLI display: "Day X, Session Y"
- Update tests to match new calendar-day assertions

### Out of Scope
- DB schema changes
- CHANGELOG or migration scripts for existing bundles
- Calibration bundle layout (cal-NNN remains as-is)

## Capabilities

### Modified Capabilities
- `paper-trading`: REQ-PT-005 bundle layout → `dia-NNN/sesion-MMM/` subdirectory (was flat `dia-NNN/` + HHMMSS suffixes). REQ-PT-008 day counter → calendar math (was session COUNT). REQ-PT-006 display → "Day X, Session Y". REQ-PT-012 report model → adds `session_number: int`.

## Approach

```python
DAY_ZERO = date(2026, 7, 28)  # frozen, per B1

def _compute_calendar_day(self) -> int:
    return (date.today() - DAY_ZERO).days + 1

def _compute_session_number(self, domain: str) -> int:
    row = self._db.execute(
        "SELECT COUNT(*) FROM reflection_reports "
        "WHERE domain = ? AND DATE(created_at) = DATE('now')",
        [domain],
    ).fetchone()
    return (int(row[0]) if row and row[0] else 0) + 1
```

Frozen date math (A1 deterministic), session count from DB (single mechanism, A5). No dual-source reconciliation.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/trady_ai/paper_trading/session.py` | Modified | New `_compute_calendar_day()`, `_compute_session_number()` |
| `src/trady_ai/paper_trading/models.py` | Modified | `SessionReport` + `session_number: int` |
| `src/trady_ai/paper_trading/bundler.py` | Modified | Path → `dia-{day}/sesion-{session}/` |
| `src/trady_ai/cli/main.py` | Modified | Display "Day X, Session Y" |
| `tests/` | Modified | Update `_compute_day` assertions |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| DAY_ZERO drift if frozen date wrong | Low | Hardcoded, code review |
| Existing bundle dirs from wrong day counter | Low | New layout — no collision; old bundles archived separately |

## Rollback Plan

Revert commit. DAY_ZERO is a single constant; `_compute_day()` name changes — callers are explicit. No DB migration.

## Dependencies

None — self-contained fix in paper_trading module.

## Success Criteria

- [ ] `_compute_calendar_day()` returns 1 on DAY_ZERO, 2 the next day
- [ ] `_compute_session_number()` increments per session within same calendar day
- [ ] Bundle path `dia-{correct_day}/sesion-{correct_session}/` — zero overwrites for 96 sessions/day
- [ ] CLI shows "Day X, Session Y"
- [ ] All existing tests pass with updated assertions
