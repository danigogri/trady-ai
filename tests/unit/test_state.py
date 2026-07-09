from datetime import datetime
from decimal import Decimal

from trady_ai.core.models import MarketInput
from trady_ai.core.state import MarketStateTracker


def _input(
    market_id: str = "btc-usd",
    price: str = "100.00",
    volume: str = "1000",
    ts: datetime | None = None,
) -> MarketInput:
    return MarketInput(
        timestamp=ts or datetime(2024, 1, 1, 12, 0, 0),
        market_id=market_id,
        price=Decimal(price),
        volume=Decimal(volume),
    )


class TestStateTrackerFirstTick:
    def test_first_tick_is_neutral(self):
        """First tick for a market → NEUTRAL, previous_state=None."""
        tracker = MarketStateTracker()
        result = tracker.update(_input())

        assert result.state == "NEUTRAL"
        assert result.previous_state is None
        assert result.market_id == "btc-usd"

    def test_first_tick_preserves_price_and_volume(self):
        """First tick preserves price and volume in MarketState."""
        tracker = MarketStateTracker()
        inp = _input(price="50000.00", volume="100.50")
        result = tracker.update(inp)

        assert result.price == Decimal("50000.00")
        assert result.volume == Decimal("100.50")


class TestStateTrackerUp:
    def test_price_above_threshold_is_up(self):
        """Price increase above threshold → UP."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        tracker.update(_input(price="100.00"))  # first tick → NEUTRAL
        result = tracker.update(_input(price="100.20"))  # +0.2% > 0.1%

        assert result.state == "UP"

    def test_exact_threshold_boundary_up(self):
        """Price increase exactly at threshold → NEUTRAL (not strictly greater)."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        tracker.update(_input(price="100.00"))
        result = tracker.update(_input(price="100.10"))  # +0.1% == threshold

        assert result.state == "NEUTRAL"


class TestStateTrackerDown:
    def test_price_below_negative_threshold_is_down(self):
        """Price decrease below -threshold → DOWN."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        tracker.update(_input(price="100.00"))
        result = tracker.update(_input(price="99.80"))  # -0.2% < -0.1%

        assert result.state == "DOWN"

    def test_exact_threshold_boundary_down(self):
        """Price decrease exactly at -threshold → NEUTRAL."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        tracker.update(_input(price="100.00"))
        result = tracker.update(_input(price="99.90"))  # -0.1% == -threshold

        assert result.state == "NEUTRAL"


class TestStateTrackerNeutral:
    def test_small_change_is_neutral(self):
        """Price change within threshold → NEUTRAL."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        tracker.update(_input(price="100.00"))
        result = tracker.update(_input(price="100.05"))  # +0.05% < 0.1%

        assert result.state == "NEUTRAL"

    def test_no_change_is_neutral(self):
        """No price change → NEUTRAL."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        tracker.update(_input(price="100.00"))
        result = tracker.update(_input(price="100.00"))

        assert result.state == "NEUTRAL"


class TestStateTrackerTransition:
    def test_previous_state_preserved(self):
        """previous_state in MarketState is preserved correctly."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        first = tracker.update(_input(price="100.00"))
        assert first.previous_state is None

        second = tracker.update(_input(price="100.20"))  # UP
        assert second.previous_state == "NEUTRAL"

        third = tracker.update(_input(price="99.80"))  # DOWN
        assert third.previous_state == "UP"

        fourth = tracker.update(_input(price="100.00"))
        # From 99.80 to 100.00 is +0.2% > threshold → UP
        assert fourth.previous_state == "DOWN"

    def test_custom_threshold(self):
        """Custom threshold_pct affects classification."""
        tracker = MarketStateTracker(threshold_pct=0.01)  # 1%
        tracker.update(_input(price="100.00"))
        result = tracker.update(_input(price="100.50"))  # +0.5% < 1%

        assert result.state == "NEUTRAL"


class TestStateTrackerMultipleMarkets:
    def test_states_do_not_contaminate(self):
        """Two independent markets do not contaminate each other's states."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        tracker.update(_input(market_id="btc-usd", price="100.00"))
        tracker.update(_input(market_id="eth-usd", price="50.00"))

        btc = tracker.get_state("btc-usd")
        assert btc is not None
        assert btc.price == Decimal("100.00")
        assert btc.state == "NEUTRAL"

        eth = tracker.get_state("eth-usd")
        assert eth is not None
        assert eth.price == Decimal("50.00")
        assert eth.state == "NEUTRAL"

        # Update only BTC
        tracker.update(_input(market_id="btc-usd", price="100.20"))  # UP
        btc2 = tracker.get_state("btc-usd")
        assert btc2 is not None
        assert btc2.state == "UP"

        # ETH should still be NEUTRAL
        eth2 = tracker.get_state("eth-usd")
        assert eth2 is not None
        assert eth2.state == "NEUTRAL"


class TestStateTrackerGetState:
    def test_get_state_unknown_returns_none(self):
        """get_state for unknown market_id → None."""
        tracker = MarketStateTracker()
        assert tracker.get_state("unknown-market") is None
