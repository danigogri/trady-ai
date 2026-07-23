"""Tests for StateGenerator ABC, DirectionalStateGenerator, and VolatilityStateGenerator.

Covers:
- ABC contract enforcement
- DirectionalStateGenerator classify() logic and backward compatibility
- VolatilityStateGenerator classify() logic
- state_labels, label(), signal_for_state()
- get_generator() factory
"""

from datetime import datetime
from decimal import Decimal

import pytest

from trady_ai.core.models import MarketInput
from trady_ai.core.state import MarketStateTracker
from trady_ai.strategies.markov.state_generator import (
    DirectionalStateGenerator,
    StateGenerator,
    VolatilityStateGenerator,
    get_generator,
)


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


# ── Task 1 & 8: StateGenerator ABC ──────────────────────────────────


class TestStateGeneratorABC:
    """StateGenerator cannot be instantiated; subclass must implement abstract members."""

    def test_cannot_instantiate_abc(self):
        """StateGenerator() raises TypeError due to abstract methods."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            StateGenerator()  # type: ignore[abstract]

    def test_label_valid_index(self):
        """label(0) returns first label, label(|S|-1) returns last."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        assert g.label(0) == "UP"
        assert g.label(1) == "DOWN"
        assert g.label(2) == "NEUTRAL"

    def test_label_negative_index_raises(self):
        """label(-1) raises IndexError."""
        g = DirectionalStateGenerator()
        with pytest.raises(IndexError, match="State index -1 out of range"):
            g.label(-1)

    def test_label_out_of_bounds_raises(self):
        """label(|S|) raises IndexError."""
        g = DirectionalStateGenerator()
        with pytest.raises(IndexError, match="State index 3 out of range"):
            g.label(3)

    def test_signal_for_state_mapping(self):
        """signal_for_state maps 0→LONG, 1→SHORT, 2→NEUTRAL for directional."""
        g = DirectionalStateGenerator()
        assert g.signal_for_state(0) == "LONG"
        assert g.signal_for_state(1) == "SHORT"
        assert g.signal_for_state(2) == "NEUTRAL"

    def test_state_count_property(self):
        """state_count returns 3 for DirectionalStateGenerator."""
        g = DirectionalStateGenerator()
        assert g.state_count == 3

    def test_state_labels_property(self):
        """state_labels returns UP/DOWN/NEUTRAL for DirectionalStateGenerator."""
        g = DirectionalStateGenerator()
        assert g.state_labels == ["UP", "DOWN", "NEUTRAL"]


# ── Task 2 & 9: DirectionalStateGenerator ───────────────────────────


class TestDirectionalStateGenerator:
    """DirectionalStateGenerator wraps MarketStateTracker threshold logic identically."""

    def test_state_count(self):
        """|S| = 3."""
        g = DirectionalStateGenerator()
        assert g.state_count == 3

    def test_state_labels(self):
        """Labels are UP, DOWN, NEUTRAL."""
        g = DirectionalStateGenerator()
        assert g.state_labels == ["UP", "DOWN", "NEUTRAL"]

    def test_first_tick_is_neutral_index(self):
        """First tick for a market → index 2 (NEUTRAL)."""
        g = DirectionalStateGenerator()
        idx = g.classify(_input())
        assert idx == 2  # NEUTRAL index

    def test_price_above_threshold_is_up(self):
        """Price increase above threshold → index 0 (UP)."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(price="100.00"))  # first tick → NEUTRAL
        idx = g.classify(_input(price="100.20"))  # +0.2% > 0.1%
        assert idx == 0  # UP

    def test_price_below_threshold_is_down(self):
        """Price decrease below -threshold → index 1 (DOWN)."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="99.80"))  # -0.2% < -0.1%
        assert idx == 1  # DOWN

    def test_small_change_is_neutral(self):
        """Price change within threshold → index 2 (NEUTRAL)."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="100.05"))  # +0.05% < 0.1%
        assert idx == 2  # NEUTRAL

    def test_no_change_is_neutral(self):
        """No price change → index 2 (NEUTRAL)."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="100.00"))
        assert idx == 2  # NEUTRAL

    def test_exact_threshold_boundary_is_neutral(self):
        """Price increase exactly at threshold → NEUTRAL (not strictly greater)."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="100.10"))  # +0.1% == threshold
        assert idx == 2  # NEUTRAL

    def test_exact_negative_threshold_boundary_is_neutral(self):
        """Price decrease exactly at -threshold → NEUTRAL."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="99.90"))  # -0.1% == -threshold
        assert idx == 2  # NEUTRAL

    def test_deterministic_classification(self):
        """Same input twice → same index."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(price="100.00"))
        inp = _input(price="100.20")
        idx1 = g.classify(inp)
        # Reset prices to simulate new process with same sequence
        g2 = DirectionalStateGenerator(threshold_pct=0.001)
        g2.classify(_input(price="100.00"))
        idx2 = g2.classify(inp)
        assert idx1 == idx2

    def test_signal_for_state(self):
        """signal_for_state matches DIRECTION_MAP from old persistence.py."""
        g = DirectionalStateGenerator()
        assert g.signal_for_state(0) == "LONG"   # UP → LONG
        assert g.signal_for_state(1) == "SHORT"  # DOWN → SHORT
        assert g.signal_for_state(2) == "NEUTRAL"  # NEUTRAL → NEUTRAL

    def test_custom_threshold(self):
        """Custom threshold_pct affects classification."""
        g = DirectionalStateGenerator(threshold_pct=0.01)  # 1%
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="100.50"))  # +0.5% < 1%
        assert idx == 2  # NEUTRAL

    def test_multiple_markets_independent(self):
        """Two markets are tracked independently."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(market_id="btc-usd", price="100.00"))
        g.classify(_input(market_id="eth-usd", price="50.00"))

        btc_idx = g.classify(_input(market_id="btc-usd", price="100.20"))  # UP
        eth_idx = g.classify(_input(market_id="eth-usd", price="50.00"))   # NEUTRAL

        assert btc_idx == 0  # UP
        assert eth_idx == 2  # NEUTRAL

    def test_identical_to_market_state_tracker(self):
        """DirectionalStateGenerator produces same state labels as MarketStateTracker."""
        tracker = MarketStateTracker(threshold_pct=0.001)
        generator = DirectionalStateGenerator(threshold_pct=0.001)

        prices = ["100.00", "100.20", "99.80", "100.05", "100.00", "100.50", "99.50"]

        tracker_results = []
        for price in prices:
            state = tracker.update(_input(price=price))
            tracker_results.append(state.state)

        gen_results = []
        for price in prices:
            idx = generator.classify(_input(price=price))
            gen_results.append(generator.state_labels[idx])

        assert gen_results == tracker_results

    def test_classify_no_market_state_tracker_state_text(self):
        """classify returns int index compatible with old STATE_INDEX values."""
        g = DirectionalStateGenerator(threshold_pct=0.001)
        g.classify(_input(price="100.00"))
        idx_up = g.classify(_input(price="100.20"))
        idx_down = g.classify(_input(price="99.80"))
        idx_neutral = g.classify(_input(price="99.85"))  # +0.05% < 0.1% → NEUTRAL

        # Should match STATE_INDEX values: UP=0, DOWN=1, NEUTRAL=2
        assert idx_up == 0
        assert idx_down == 1
        assert idx_neutral == 2


# ── Task: VolatilityStateGenerator ──────────────────────────────────


class TestVolatilityStateGenerator:
    """VolatilityStateGenerator wraps VolatilityPersistence._classify_volatility logic."""

    def test_state_count(self):
        """|S| = 3."""
        g = VolatilityStateGenerator()
        assert g.state_count == 3

    def test_state_labels(self):
        """Labels are HIGH, LOW, STABLE."""
        g = VolatilityStateGenerator()
        assert g.state_labels == ["HIGH", "LOW", "STABLE"]

    def test_signal_for_state(self):
        """signal_for_state matches VOLATILITY_DIR_MAP."""
        g = VolatilityStateGenerator()
        assert g.signal_for_state(0) == "SHORT"   # HIGH → SHORT
        assert g.signal_for_state(1) == "LONG"    # LOW → LONG
        assert g.signal_for_state(2) == "NEUTRAL"  # STABLE → NEUTRAL

    def test_first_call_makes_history_and_returns_stable(self):
        """First classify call adds price and returns STABLE (no prior history)."""
        g = VolatilityStateGenerator(threshold_pct=0.01)
        idx = g.classify(_input(price="100.00"))
        assert idx == 2  # STABLE
        assert len(g._price_history) == 1  # type: ignore[attr-defined]

    def test_single_price_returns_stable(self):
        """Single price point → STABLE index."""
        g = VolatilityStateGenerator(threshold_pct=0.01)
        # First call tracks the price but returns STABLE
        idx = g.classify(_input(price="100.00"))
        assert idx == 2  # STABLE

    def test_zero_range_returns_stable(self):
        """Two identical prices → STABLE."""
        g = VolatilityStateGenerator(threshold_pct=0.01)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="100.00"))
        assert idx == 2  # STABLE

    def test_high_volatility(self):
        """Range > threshold_pct → HIGH index."""
        g = VolatilityStateGenerator(threshold_pct=0.01)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="102.00"))  # 2% > 1%
        assert idx == 0  # HIGH

    def test_low_volatility(self):
        """Range < threshold_pct * 0.5 → LOW index."""
        g = VolatilityStateGenerator(threshold_pct=0.01)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="100.03"))  # 0.03% < 0.5%
        assert idx == 1  # LOW

    def test_stable_volatility(self):
        """Range between threshold_pct*0.5 and threshold_pct → STABLE."""
        g = VolatilityStateGenerator(threshold_pct=0.01)
        g.classify(_input(price="100.00"))
        idx = g.classify(_input(price="100.80"))  # 0.8% between 0.5% and 1%
        assert idx == 2  # STABLE

    def test_window_limits_history(self):
        """Price history is bounded to volatility_window."""
        g = VolatilityStateGenerator(threshold_pct=0.01, volatility_window=3)
        g.classify(_input(price="100.00"))
        g.classify(_input(price="101.00"))
        g.classify(_input(price="102.00"))
        g.classify(_input(price="103.00"))
        g.classify(_input(price="104.00"))

        # Window of 3, so last 3 prices: 102, 103, 104
        idx = g.classify(_input(price="106.00"))  # big jump from min=102
        assert idx == 0  # HIGH


# ── Task: get_generator() factory ───────────────────────────────────


class TestGetGenerator:
    """get_generator() factory function."""

    def test_directional_generator(self):
        """get_generator('directional') returns DirectionalStateGenerator."""
        g = get_generator("directional")
        assert isinstance(g, DirectionalStateGenerator)
        assert g.state_count == 3

    def test_volatility_generator(self):
        """get_generator('volatility') returns VolatilityStateGenerator."""
        g = get_generator("volatility")
        assert isinstance(g, VolatilityStateGenerator)
        assert g.state_count == 3

    def test_unknown_generator_raises(self):
        """get_generator('unknown') raises ValueError."""
        with pytest.raises(ValueError, match="Unknown state generator"):
            get_generator("unknown")

    def test_directional_with_state_space(self):
        """get_generator accepts state_space_size parameter."""
        g = get_generator("directional", state_space_size=3)
        assert isinstance(g, DirectionalStateGenerator)

    def test_volatility_with_state_space(self):
        """get_generator with volatility accepts state_space_size."""
        g = get_generator("volatility", state_space_size=3)
        assert isinstance(g, VolatilityStateGenerator)

    def test_rejects_state_space_size_below_2(self):
        """get_generator raises ValueError when state_space_size < 2."""
        with pytest.raises(ValueError, match="state_space_size must be >= 2"):
            get_generator("directional", state_space_size=1)

        with pytest.raises(ValueError, match="state_space_size must be >= 2"):
            get_generator("directional", state_space_size=0)
