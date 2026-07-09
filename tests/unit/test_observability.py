from datetime import datetime, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import pytest

from trady_ai.core.models import ExecutionDecision, Position
from trady_ai.core.observability import compute_summary


def _make_decision(action: str = "HOLD") -> ExecutionDecision:
    dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    return ExecutionDecision(
        signal_id=uuid5(NAMESPACE_URL, f"signal:{action}:{dt.isoformat()}"),
        action=action,
        reason="test",
        risk_check_passed=True,
        risk_check_details={},
        timestamp=dt,
    )


def _make_position(
    market_id: str = "btc-usd",
    status: str = "OPEN",
    pnl: Decimal | None = None,
) -> Position:
    dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    return Position(
        id=uuid5(NAMESPACE_URL, f"pos:{market_id}:{dt.isoformat()}"),
        market_id=market_id,
        direction="LONG",
        entry_price=Decimal("100"),
        current_price=Decimal("100"),
        size=Decimal("10"),
        pnl=pnl,
        status=status,
        signal_id=uuid5(NAMESPACE_URL, f"sig:{market_id}:{dt.isoformat()}"),
    )


def test_compute_summary_empty():
    """No data → summary with zeros."""
    summary = compute_summary([], [], [])
    assert summary["total_signals"] == 0
    assert summary["total_trades"] == 0
    assert summary["open_positions"] == 0
    assert summary["closed_positions"] == 0
    assert summary["win_rate"] == 0.0
    assert summary["total_pnl"] == 0.0


def test_compute_summary_win_rate():
    """3 closed positions, 2 with P&L > 0 → win_rate = 2/3."""
    positions = [
        _make_position("a", "CLOSED", Decimal("10.00")),
        _make_position("b", "CLOSED", Decimal("-5.00")),
        _make_position("c", "CLOSED", Decimal("3.00")),
    ]
    decisions = [_make_decision("OPEN_LONG") for _ in range(3)]
    summary = compute_summary(decisions, [], positions)
    assert summary["win_rate"] == pytest.approx(2 / 3)
    assert summary["closed_positions"] == 3


def test_compute_summary_total_pnl():
    """total_pnl = sum of all closed position P&Ls."""
    positions = [
        _make_position("a", "CLOSED", Decimal("15.00")),
        _make_position("b", "CLOSED", Decimal("-8.00")),
    ]
    decisions = [_make_decision() for _ in range(2)]
    summary = compute_summary(decisions, [], positions)
    assert summary["total_pnl"] == 7.0


def test_compute_summary_signals_by_direction():
    """Counts per action are correct."""
    decisions = [
        _make_decision("OPEN_LONG"),
        _make_decision("OPEN_LONG"),
        _make_decision("REJECT"),
        _make_decision("HOLD"),
    ]
    summary = compute_summary(decisions, [], [])
    assert summary["signals_by_direction"] == {
        "OPEN_LONG": 2,
        "REJECT": 1,
        "HOLD": 1,
    }
