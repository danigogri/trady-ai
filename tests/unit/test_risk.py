from datetime import datetime, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import pytest

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.models import ExecutionDecision, Position, Signal
from trady_ai.core.risk import RiskEnforcer


def _make_signal(direction: str = "LONG", market_id: str = "btc-usd") -> Signal:
    dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    return Signal(
        id=uuid5(NAMESPACE_URL, f"test:{market_id}:{dt.isoformat()}"),
        timestamp=dt,
        market_id=market_id,
        direction=direction,
        confidence=0.65,
        strategy_name="test",
    )


def _make_position(market_id: str = "btc-usd", direction: str = "LONG", status: str = "OPEN") -> Position:
    dt = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)
    return Position(
        id=uuid5(NAMESPACE_URL, f"position:{market_id}:{dt.isoformat()}"),
        market_id=market_id,
        direction=direction,
        entry_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        size=Decimal("10.00"),
        pnl=None,
        status=status,
        signal_id=uuid5(NAMESPACE_URL, f"signal:{market_id}:{dt.isoformat()}"),
    )


def test_risk_enforcer_allow():
    """Signal LONG, no open positions → OPEN_LONG."""
    enforcer = RiskEnforcer()
    signal = _make_signal("LONG")
    config = RuntimeConfig(position_size=Decimal("10.00"))

    decision = enforcer.evaluate(signal, [], config)

    assert decision.action == "OPEN_LONG"
    assert decision.risk_check_passed is True


def test_risk_enforcer_reject_max_positions():
    """Signal LONG, 1 open position, max=1 → REJECT."""
    enforcer = RiskEnforcer(max_open_positions=1)
    signal = _make_signal("LONG", "eth-usd")
    positions = [_make_position("btc-usd")]
    config = RuntimeConfig(position_size=Decimal("10.00"))

    decision = enforcer.evaluate(signal, positions, config)

    assert decision.action == "REJECT"
    assert decision.risk_check_passed is False
    assert "Max open positions" in decision.reason


def test_risk_enforcer_reject_duplicate_market():
    """Signal for a market that already has an OPEN position → REJECT."""
    enforcer = RiskEnforcer(max_open_positions=5)
    signal = _make_signal("LONG", "btc-usd")
    positions = [_make_position("btc-usd")]
    config = RuntimeConfig(position_size=Decimal("10.00"))

    decision = enforcer.evaluate(signal, positions, config)

    assert decision.action == "REJECT"
    assert decision.risk_check_passed is False
    assert "already open" in decision.reason.lower()


def test_risk_enforcer_neutral_hold():
    """Signal NEUTRAL → HOLD immediately."""
    enforcer = RiskEnforcer()
    signal = _make_signal("NEUTRAL")
    config = RuntimeConfig()

    decision = enforcer.evaluate(signal, [], config)

    assert decision.action == "HOLD"
    assert decision.risk_check_passed is True


def test_risk_enforcer_stop_loss():
    """LONG position with current_price < 95% entry → CLOSE."""
    enforcer = RiskEnforcer(max_open_positions=10)  # C1 must not reject
    signal = _make_signal("LONG", "eth-usd")         # different market to avoid C4
    pos = _make_position("btc-usd")
    pos.current_price = Decimal("94.00")  # 6% drop → triggers 5% stop loss
    positions = [pos]
    config = RuntimeConfig(stop_loss_pct=0.05, position_size=Decimal("10.00"))

    decision = enforcer.evaluate(signal, positions, config)

    assert decision.action == "CLOSE"
    assert "Stop loss" in decision.reason


def test_risk_enforcer_fail_fast_invalid_config():
    """RuntimeConfig with position_size=0 rejected at construction (Pydantic guard)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RuntimeConfig(position_size=Decimal("0"))
