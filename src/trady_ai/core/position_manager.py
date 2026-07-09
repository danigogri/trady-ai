from decimal import ROUND_HALF_EVEN, Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.models import Position, Signal


class PositionManager:
    """In-memory lifecycle management for positions.

    Stores positions in a dict[UUID, Position] for O(1) lookups.
    The database is written by the engine via persistence functions —
    this class is the runtime source of truth, not the DB.
    """

    def __init__(self):
        self._positions: dict[UUID, Position] = {}

    def open_position(self, signal: Signal, price: Decimal, size: Decimal, config: RuntimeConfig) -> Position:
        """Open a new position from a signal.

        UUID5 is deterministic: uuid5(NURL, f"position:{market_id}:{signal.id}").
        """
        pos_id = uuid5(NAMESPACE_URL, f"position:{signal.market_id}:{signal.id}")
        direction = "LONG" if signal.direction == "LONG" else "SHORT"
        position = Position(
            id=pos_id,
            market_id=signal.market_id,
            direction=direction,
            entry_price=price,
            current_price=price,
            size=size,
            pnl=None,
            status="OPEN",
            signal_id=signal.id,
        )
        self._positions[position.id] = position
        return position

    def close_position(self, position: Position, exit_price: Decimal, config: RuntimeConfig) -> Position:
        """Close an open position, computing P&L.

        Mutates the position in-place and updates the internal dict.
        """
        pnl = self.compute_pnl(
            position.entry_price,
            exit_price,
            position.size,
            config.transaction_cost_pct,
            position.direction,
        )
        position.current_price = exit_price
        position.pnl = pnl
        position.status = "CLOSED"
        self._positions[position.id] = position
        return position

    def get_open_positions(self) -> list[Position]:
        """Return all positions with status == 'OPEN'."""
        return [p for p in self._positions.values() if p.status == "OPEN"]

    def get_all_positions(self) -> list[Position]:
        """Return all positions (open and closed)."""
        return list(self._positions.values())

    @staticmethod
    def compute_pnl(
        entry: Decimal, exit: Decimal, size: Decimal, cost_pct: float, direction: str
    ) -> Decimal:
        """Compute net P&L for a position.

        Formula:
          LONG:  gross = (exit - entry) * size / entry
          SHORT: gross = (entry - exit) * size / entry
          cost = abs(gross) * Decimal(str(cost_pct))
          net = (gross - cost), quantized to 8 decimal places.
        """
        if direction == "LONG":
            gross = (exit - entry) * size / entry
        else:
            gross = (entry - exit) * size / entry
        cost = abs(gross) * Decimal(str(cost_pct))
        return (gross - cost).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
