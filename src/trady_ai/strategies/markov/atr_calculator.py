"""ATRCalculator — deterministic ATR-based threshold for MarketStateClassifier.

Computes τ = α × ATR / price, where ATR is the mean of absolute price changes
over the most recent N-1 intervals (N configured ticks).  Uses a per-market_id
circular buffer to store prices.

Design decision D-003 (measurement-calibration):
  - ATR via mean absolute price change (not full OHLC)
  - Helper class consumed by both MarketStateTracker and DirectionalStateGenerator
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal


class ATRCalculator:
    """Deterministic ATR-based threshold calculator.

    Parameters:
        alpha:     Multiplier for the ATR (default 2.0 per REQ-MC-002).
        period:    Number of recent absolute changes averaged (default 20).
        buffer_size:  Max prices retained per market (default 1000).

    Thread-safety: Not required — used sequentially per session.
    """

    def __init__(
        self,
        alpha: float = 2.0,
        period: int = 20,
        buffer_size: int = 1000,
    ) -> None:
        self.alpha = Decimal(str(alpha))
        self.period = period
        self.buffer_size = buffer_size
        self._buffers: defaultdict[str, list[Decimal]] = defaultdict(list)

    def update(self, market_id: str, price: Decimal) -> Decimal | None:
        """Process a new price tick for *market_id*.

        Returns:
            τ = α × ATR / price on the second and subsequent ticks,
            or ``None`` on the first tick (no previous price to compute change).
        """
        buf = self._buffers[market_id]

        if not buf:
            # First tick — record price only
            buf.append(price)
            return None

        buf.append(price)

        # Enforce circular-buffer limit
        if len(buf) > self.buffer_size:
            buf[:] = buf[-self.buffer_size:]

        return self.threshold(market_id)

    def threshold(self, market_id: str) -> Decimal:
        """Return the current threshold τ for *market_id*.

        Returns ``Decimal('0')`` if there is insufficient data (fewer than 2
        prices buffered) — the caller (e.g. MarketStateTracker) will fall
        back to a static threshold in that case.
        """
        buf = self._buffers.get(market_id)
        if not buf or len(buf) < 2:
            return Decimal("0")

        # Compute absolute price changes over the buffer
        changes = [abs(buf[i + 1] - buf[i]) for i in range(len(buf) - 1)]

        # Take only the most recent `period` changes
        recent = changes[-self.period:] if len(changes) > self.period else changes

        atr = sum(recent, Decimal("0")) / Decimal(str(len(recent)))
        current_price = buf[-1]

        return self.alpha * atr / current_price

    def clear(self, market_id: str) -> None:
        """Remove all buffered data for *market_id*."""
        self._buffers.pop(market_id, None)
