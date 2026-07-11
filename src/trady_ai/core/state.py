from decimal import Decimal
from typing import Literal, cast

from trady_ai.core.models import MarketInput, MarketState


class MarketStateTracker:
    """Tracks the latest MarketState per market and classifies transitions.

    For each new MarketInput, computes price change percentage against the
    previous price for that market and classifies the state as UP, DOWN, or
    NEUTRAL based on the configured threshold. The first tick for any market
    is always NEUTRAL (no previous price to compare against).
    """

    def __init__(self, threshold_pct: float = 0.001):
        self._states: dict[str, MarketState] = {}
        self._threshold_pct = threshold_pct

    def update(self, market_input: MarketInput) -> MarketState:
        """Process a new MarketInput and return the classified MarketState.

        First tick for a market → NEUTRAL with previous_state=None.
        Subsequent ticks → UP/DOWN/NEUTRAL based on change_pct vs threshold.
        """
        market_id = market_input.market_id
        previous_state = self._states.get(market_id)

        if previous_state is None:
            state_label = "NEUTRAL"
            prev_state_value = None
        else:
            prev_price = previous_state.price
            new_price = market_input.price
            change_pct = (new_price - prev_price) / prev_price

            if change_pct > Decimal(str(self._threshold_pct)):
                state_label = "UP"
            elif change_pct < -Decimal(str(self._threshold_pct)):
                state_label = "DOWN"
            else:
                state_label = "NEUTRAL"

            prev_state_value = previous_state.state

        new_state = MarketState(
            market_id=market_id,
            timestamp=market_input.timestamp,
            price=market_input.price,
            volume=market_input.volume,
            state=cast(Literal["UP", "DOWN", "NEUTRAL"], state_label),
            previous_state=prev_state_value,
        )
        self._states[market_id] = new_state
        return new_state

    def get_state(self, market_id: str) -> MarketState | None:
        """Return the latest MarketState for a market, or None if unknown."""
        return self._states.get(market_id)
