from decimal import Decimal
from typing import Literal, cast

from trady_ai.core.models import MarketInput, MarketState
from trady_ai.strategies.markov.atr_calculator import ATRCalculator


class MarketStateTracker:
    """Tracks the latest MarketState per market and classifies transitions.

    For each new MarketInput, computes price change percentage against the
    previous price for that market and classifies the state as UP, DOWN, or
    NEUTRAL based on the configured threshold.

    Threshold can be either:
      - **ATR-based** (default): ``τ = α × ATR / price``, where ATR is the
        mean absolute price change over the last ``atr_period`` ticks.
      - **Static** (backward compat): ``threshold_pct`` — a fixed percentage.

    When the ATRCalculator has insufficient data (fewer than 2 ticks), the
    static ``threshold_pct`` is used as fallback. The first tick for any
    market is always NEUTRAL (no previous price to compare against).

    Args:
        threshold_pct: Static fallback threshold (fraction, default 0.001).
        alpha:         ATR multiplier (default 2.0, REQ-MC-002).
        atr_period:    Number of recent absolute changes for ATR (default 20).
    """

    def __init__(
        self,
        threshold_pct: float = 0.001,
        *,
        alpha: float | None = None,
        atr_period: int = 20,
    ):
        self._states: dict[str, MarketState] = {}
        self._threshold_pct = threshold_pct
        self._atr = (
            ATRCalculator(alpha=alpha, period=atr_period)
            if alpha is not None
            else None
        )

    def update(self, market_input: MarketInput) -> MarketState:
        """Process a new MarketInput and return the classified MarketState.

        First tick for a market → NEUTRAL with previous_state=None.
        Subsequent ticks → UP/DOWN/NEUTRAL based on the effective threshold
        (ATR τ when available, else ``threshold_pct``).
        """
        market_id = market_input.market_id
        previous_state = self._states.get(market_id)
        price = market_input.price

        # Compute ATR-based τ when ATR is configured
        τ = self._atr.update(market_id, price) if self._atr is not None else None

        if previous_state is None:
            state_label = "NEUTRAL"
            prev_state_value = None
        else:
            prev_price = previous_state.price
            change_pct = (price - prev_price) / prev_price

            # Effective threshold: ATR τ if available, else static fallback
            effective = τ if τ is not None else Decimal(str(self._threshold_pct))

            if change_pct > effective:
                state_label = "UP"
            elif change_pct < -effective:
                state_label = "DOWN"
            else:
                state_label = "NEUTRAL"

            prev_state_value = previous_state.state

        new_state = MarketState(
            market_id=market_id,
            timestamp=market_input.timestamp,
            price=price,
            volume=market_input.volume,
            state=cast(Literal["UP", "DOWN", "NEUTRAL"], state_label),
            previous_state=prev_state_value,
        )
        self._states[market_id] = new_state
        return new_state

    def get_state(self, market_id: str) -> MarketState | None:
        """Return the latest MarketState for a market, or None if unknown."""
        return self._states.get(market_id)
