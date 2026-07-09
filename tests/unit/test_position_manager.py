from datetime import datetime, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.models import Position, Signal
from trady_ai.core.position_manager import PositionManager


def _make_signal(direction: str = "LONG", market_id: str = "btc-usd") -> Signal:
    dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    return Signal(
        id=uuid5(NAMESPACE_URL, f"test_signal:{market_id}:{dt.isoformat()}"),
        timestamp=dt,
        market_id=market_id,
        direction=direction,
        confidence=0.65,
        strategy_name="test",
    )


def _make_config(
    position_size: str = "10.00",
    transaction_cost_pct: float = 0.0,
    stop_loss_pct: float = 0.05,
) -> RuntimeConfig:
    return RuntimeConfig(
        position_size=Decimal(position_size),
        transaction_cost_pct=transaction_cost_pct,
        stop_loss_pct=stop_loss_pct,
    )


# -- P&L computation tests --

def test_pnl_long_profit():
    """entry=100, exit=110, size=10, cost=0% → P&L = 1.00000000."""
    pnl = PositionManager.compute_pnl(
        Decimal("100"), Decimal("110"), Decimal("10"), 0.0, "LONG"
    )
    assert pnl == Decimal("1.00000000")


def test_pnl_long_loss():
    """entry=100, exit=90, size=10, cost=0% → P&L = -1.00000000."""
    pnl = PositionManager.compute_pnl(
        Decimal("100"), Decimal("90"), Decimal("10"), 0.0, "LONG"
    )
    assert pnl == Decimal("-1.00000000")


def test_pnl_short_profit():
    """entry=100, exit=90, size=10, cost=0% → P&L = 1.00000000."""
    pnl = PositionManager.compute_pnl(
        Decimal("100"), Decimal("90"), Decimal("10"), 0.0, "SHORT"
    )
    assert pnl == Decimal("1.00000000")


def test_pnl_with_cost():
    """entry=100, exit=110, size=10, cost_pct=0.001 → P&L = gross - cost."""
    pnl = PositionManager.compute_pnl(
        Decimal("100"), Decimal("110"), Decimal("10"), 0.001, "LONG"
    )
    # gross = (110-100)*10/100 = 1.0, cost = abs(1.0)*0.001 = 0.001, net = 0.99900000
    assert pnl == Decimal("0.99900000")


# -- Lifecycle tests --

def test_round_close():
    """Open position → close it → status=CLOSED, pnl is not None."""
    pm = PositionManager()
    signal = _make_signal("LONG", "btc-usd")
    config = _make_config()

    pos = pm.open_position(signal, Decimal("100.00"), Decimal("10.00"), config)
    assert pos.status == "OPEN"
    assert pos.pnl is None

    closed = pm.close_position(pos, Decimal("110.00"), config)
    assert closed.status == "CLOSED"
    assert closed.pnl is not None
    assert closed.pnl > 0


def test_get_open():
    """Open 2 positions, close 1 → get_open_positions returns 1."""
    pm = PositionManager()
    sig1 = _make_signal("LONG", "btc-usd")
    sig2 = _make_signal("SHORT", "eth-usd")
    config = _make_config()

    pos1 = pm.open_position(sig1, Decimal("100.00"), Decimal("10.00"), config)
    pm.open_position(sig2, Decimal("50.00"), Decimal("5.00"), config)

    assert len(pm.get_open_positions()) == 2

    pm.close_position(pos1, Decimal("110.00"), config)
    assert len(pm.get_open_positions()) == 1
    assert len(pm.get_all_positions()) == 2
