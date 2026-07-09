import collections
from decimal import Decimal

from trady_ai.core.models import ExecutionDecision, Position, Trade


def compute_summary(
    decisions: list[ExecutionDecision],
    trades: list[Trade],
    positions: list[Position],
) -> dict:
    """Compute summary statistics after an engine run.

    Returns:
        dict with keys:
            total_signals, signals_by_direction, total_trades,
            open_positions, closed_positions, win_rate, total_pnl, max_drawdown.
    """
    closed = [p for p in positions if p.status == "CLOSED" and p.pnl is not None]
    wins = sum(1 for p in closed if p.pnl > 0)
    pnl_total = sum((p.pnl for p in closed), Decimal("0"))

    direction_counts = dict(collections.Counter(d.action for d in decisions))

    # Max drawdown: iterate closed positions chronologically
    running_pnl = Decimal("0")
    peak = Decimal("0")
    max_drawdown = Decimal("0")
    for p in closed:
        running_pnl += p.pnl
        if running_pnl > peak:
            peak = running_pnl
        drawdown = peak - running_pnl
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "total_signals": len(decisions),
        "signals_by_direction": direction_counts,
        "total_trades": len(trades),
        "open_positions": sum(1 for p in positions if p.status == "OPEN"),
        "closed_positions": len(closed),
        "win_rate": wins / len(closed) if closed else 0.0,
        "total_pnl": float(pnl_total),
        "max_drawdown": float(max_drawdown),
    }
