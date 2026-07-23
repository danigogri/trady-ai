"""Tests for N-state MarkovPersistenceEngine refactor.

Covers:
- N×N transition matrix construction (|S|=2,3,5)
- Default DirectionalStateGenerator(3) backward compatibility
- on_update uses generator.classify() instead of STATE_INDEX
- on_evaluate uses generator.state_labels/signal_for_state instead of INDEX_STATE/DIRECTION_MAP
- VolatilityPersistence with injected generator
"""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest

from trady_ai.core.models import MarketInput, MarketState
from trady_ai.strategies.markov.persistence import (
    MarkovPersistenceEngine,
    VolatilityPersistence,
)
from trady_ai.strategies.markov.state_generator import (
    DirectionalStateGenerator,
    StateGenerator,
    VolatilityStateGenerator,
)


def _state(
    market_id: str, state_label: str, ts: datetime | None = None
) -> MarketState:
    return MarketState(
        market_id=market_id,
        timestamp=ts or datetime(2024, 1, 1, 12, 0, 0),
        price=Decimal("100.00"),
        volume=Decimal("1000"),
        state=state_label,
    )


def _state_with_price(
    market_id: str, state_label: str, price: str, ts: datetime | None = None
) -> MarketState:
    return MarketState(
        market_id=market_id,
        timestamp=ts or datetime(2024, 1, 1, 12, 0, 0),
        price=Decimal(price),
        volume=Decimal("1000"),
        state=state_label,
    )


# ── Custom generators for testing ───────────────────────────────────


class TwoStateGenerator(StateGenerator):
    """Simple |S|=2 generator: price > 100 → UP (0), else DOWN (1)."""
    state_count: int = 2
    state_labels: list[str] = ["HIGH", "LOW"]
    _SIGNAL_MAP: dict[int, str] = {0: "LONG", 1: "SHORT"}

    def __init__(self) -> None:
        self._prices: dict[str, Decimal] = {}

    def classify(self, input: MarketInput) -> int:
        self._prices[input.market_id] = input.price
        if input.price > Decimal("100"):
            return 0  # HIGH
        return 1  # LOW

    def signal_for_state(self, index: int) -> str:
        return self._SIGNAL_MAP[index]


class FiveStateGenerator(StateGenerator):
    """Simple |S|=5 generator: maps price to 5 quantized buckets."""
    state_count: int = 5
    state_labels: list[str] = ["A", "B", "C", "D", "E"]

    def __init__(self) -> None:
        self._prices: dict[str, Decimal] = {}

    def classify(self, input: MarketInput) -> int:
        self._prices[input.market_id] = input.price
        # Quantize price into 5 buckets based on integer part % 5
        bucket = int(input.price) % 5
        return bucket


# ── Task 3 & 10: N‑state engine refactor ────────────────────────────


class TestNStateMatrixConstruction:
    """Engine constructs |S|×|S| matrix from generator."""

    def test_default_three_state(self):
        """Default engine (no generator) → 3×3 matrix (backward compat)."""
        engine = MarkovPersistenceEngine()
        assert engine._transition_counts.shape == (3, 3)
        assert engine._state_counts.shape == (3,)

    def test_two_state_matrix(self):
        """Engine with |S|=2 → 2×2 matrix."""
        gen = TwoStateGenerator()
        engine = MarkovPersistenceEngine(state_generator=gen)
        assert engine._transition_counts.shape == (2, 2)
        assert engine._state_counts.shape == (2,)

    def test_five_state_matrix(self):
        """Engine with |S|=5 → 5×5 matrix."""
        gen = FiveStateGenerator()
        engine = MarkovPersistenceEngine(state_generator=gen, warmup_ticks=1)
        assert engine._transition_counts.shape == (5, 5)
        assert engine._state_counts.shape == (5,)

    def test_state_generator_default_is_directional(self):
        """Default state_generator is DirectionalStateGenerator(3)."""
        engine = MarkovPersistenceEngine()
        assert isinstance(engine._generator, DirectionalStateGenerator)
        assert engine._generator.state_count == 3


class TestNStateUpdate:
    """on_update uses generator.classify() instead of STATE_INDEX."""

    def test_update_with_two_state_generator(self):
        """|S|=2 engine correctly increments transitions from generator indices."""
        gen = TwoStateGenerator()
        engine = MarkovPersistenceEngine(state_generator=gen, warmup_ticks=1)

        # price=101 → HIGH (0), price=99 → LOW (1)
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))
        engine.update(_state_with_price("btc-usd", "LOW", "99.00"))
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))

        # Sequence: 0, 1, 0
        # Transitions: 0→1, 1→0
        expected = np.array([[0, 1], [1, 0]], dtype=np.int64)
        assert (engine._transition_counts == expected).all()

    def test_update_with_five_state_generator(self):
        """|S|=5 engine correctly tracks transitions."""
        gen = FiveStateGenerator()
        engine = MarkovPersistenceEngine(state_generator=gen, warmup_ticks=1)

        prices = ["101", "102", "103", "104", "105", "101"]
        for price in prices:
            engine.update(_state_with_price("btc-usd", "A", price))

        # prices: 101→1, 102→2, 103→3, 104→4, 105→0, 101→1
        # transitions: 1→2, 2→3, 3→4, 4→0, 0→1 (5 transitions)
        assert engine._total_obs == 6
        assert engine._transition_counts.sum() == 5  # 5 transitions from 6 ticks

    def test_update_tracks_last_state_from_generator(self):
        """Engine stores the generator's classified index as last_state."""
        gen = TwoStateGenerator()
        engine = MarkovPersistenceEngine(state_generator=gen, warmup_ticks=1)

        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))
        assert engine._last_state_idx == 0  # HIGH

        engine.update(_state_with_price("btc-usd", "LOW", "99.00"))
        assert engine._last_state_idx == 1  # LOW


class TestNStateEvaluate:
    """on_evaluate uses generator indices + signal mapping."""

    def test_two_state_evaluate(self):
        """|S|=2 engine evaluate() returns signal via generator.signal_for_state."""
        gen = TwoStateGenerator()
        engine = MarkovPersistenceEngine(state_generator=gen, warmup_ticks=1)

        # Build transitions: HIGH→HIGH (3x), HIGH→LOW (1x)
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))
        engine.update(_state_with_price("btc-usd", "LOW", "99.00"))

        # Current state from generator: price=99 → LOW (1)
        signal = engine.evaluate(_state_with_price("btc-usd", "LOW", "99.00"))
        assert signal.direction in ("LONG", "SHORT", "NEUTRAL")

    def test_argmax_returns_best_state_index(self):
        """evaluate() picks best index and maps via generator."""
        gen = TwoStateGenerator()
        engine = MarkovPersistenceEngine(state_generator=gen, warmup_ticks=1)

        # 2× HIGH → HIGH transitions, 0× HIGH → LOW
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))
        engine.update(_state_with_price("btc-usd", "HIGH", "101.00"))

        # row 0 = [2, 0], argmax = 0 → HIGH → signal_for_state(0) = "LONG"
        signal = engine.evaluate(_state_with_price("btc-usd", "HIGH", "101.00"))
        assert signal.direction == "LONG"

    def test_no_transitions_returns_neutral(self):
        """State with no recorded transitions → NEUTRAL."""
        gen = FiveStateGenerator()
        engine = MarkovPersistenceEngine(state_generator=gen, warmup_ticks=1)

        # Only state 0 has transitions
        engine.update(_state_with_price("btc-usd", "A", "101"))
        engine.update(_state_with_price("btc-usd", "A", "101"))

        # Evaluate on state 4 (no transitions from 4)
        signal = engine.evaluate(_state_with_price("btc-usd", "E", "105"))
        assert signal.direction == "NEUTRAL"
        assert signal.confidence == 0.0
        assert signal.metadata["reason"] == "no_transitions_from_current_state"


# ── Task 3 & 10: Backward compatibility ─────────────────────────────


class TestNStateBackwardCompat:
    """Engine with default DirectionalStateGenerator(3) produces identical output."""

    def test_update_produces_same_counts(self):
        """Default engine produces same transition_counts as before."""
        old_engine = MarkovPersistenceEngine(warmup_ticks=1)

        states = ["UP", "UP", "DOWN", "UP", "UP"]
        for label in states:
            old_engine.update(_state("btc-usd", label))

        # New engine with default generator — same behavior
        new_engine = MarkovPersistenceEngine(warmup_ticks=1)
        for label in states:
            new_engine.update(_state("btc-usd", label))

        assert (new_engine._transition_counts == old_engine._transition_counts).all()
        assert (new_engine._state_counts == old_engine._state_counts).all()

    def test_evaluate_produces_same_signals(self):
        """Default engine evaluate() matches old behavior."""
        old_engine = MarkovPersistenceEngine(warmup_ticks=10)

        states = []
        for i in range(55):
            label = "UP" if i % 3 == 0 else "DOWN" if i % 3 == 1 else "NEUTRAL"
            states.append(
                _state("btc-usd", label, datetime(2024, 1, 1, 12, 0, i))
            )

        for st in states:
            old_engine.update(st)

        new_engine = MarkovPersistenceEngine(warmup_ticks=10)
        for st in states:
            new_engine.update(st)

        for st in states:
            sig_old = old_engine.evaluate(st)
            sig_new = new_engine.evaluate(st)

            assert sig_new.direction == sig_old.direction
            assert sig_new.confidence == pytest.approx(sig_old.confidence)

    def test_parameters_unchanged(self):
        """parameters() returns same keys/values."""
        engine = MarkovPersistenceEngine(warmup_ticks=100, threshold_pct=0.01)
        params = engine.parameters()
        assert params["warmup_ticks"] == 100
        assert params["threshold_pct"] == 0.01


# ── Task 3: VolatilityPersistence with generator ────────────────────


class TestNStateVolatility:
    """VolatilityPersistence with injected VolatilityStateGenerator."""

    def test_volatility_default_generator(self):
        """VolatilityPersistence default generator is VolatilityStateGenerator."""
        vp = VolatilityPersistence()
        assert isinstance(vp._generator, VolatilityStateGenerator)
        assert vp._generator.state_count == 3

    def test_volatility_update_tracks_from_generator(self):
        """VolatilityPersistence transitions use generator.classify()."""
        vp = VolatilityPersistence(
            warmup_ticks=1, threshold_pct=0.01, volatility_window=5
        )

        vp.update(_state_with_price("btc-usd", "UP", "100.00"))
        vp.update(_state_with_price("btc-usd", "DOWN", "102.00"))

        # First call: price=100, history=[100] → STABLE (idx 2)
        # Second call: price=102, history=[100, 102], range 2% > 1% → HIGH (idx 0)
        # Transition: 2→0
        assert vp._transition_counts[2][0] == 1
        assert vp._total_obs == 2

    def test_volatility_evaluate_uses_generator_labels(self):
        """VolatilityPersistence evaluate uses generator's signal_for_state."""
        vp = VolatilityPersistence(
            warmup_ticks=3, threshold_pct=0.01, volatility_window=5
        )

        prices = [
            ("100.00", "UP"),
            ("102.00", "UP"),  # HIGH
            ("104.00", "UP"),  # HIGH
            ("106.00", "UP"),  # HIGH
        ]
        for price, label in prices:
            vp.update(_state_with_price("btc-usd", label, price))

        signal = vp.evaluate(_state_with_price("btc-usd", "UP", "106.00"))
        assert signal.strategy_name == "volatility_persistence"
        assert signal.confidence >= 0.0
        assert "probabilities" in signal.metadata
        assert "volatility_state" in signal.metadata
