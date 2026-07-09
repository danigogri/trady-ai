from datetime import datetime
from decimal import Decimal

import pytest

from trady_ai.core.markov_strategy import (
    MarkovStrategy,
)
from trady_ai.core.models import MarketState


def _state(market_id: str, state_label: str, ts: datetime | None = None) -> MarketState:
    return MarketState(
        market_id=market_id,
        timestamp=ts or datetime(2024, 1, 1, 12, 0, 0),
        price=Decimal("100.00"),
        volume=Decimal("1000"),
        state=state_label,
    )


class TestMarkovColdStart:
    def test_cold_start_returns_neutral_with_zero_confidence(self):
        """Before warmup_ticks reached → evaluate() returns NEUTRAL, confidence=0.0."""
        strategy = MarkovStrategy(warmup_ticks=50)
        s = _state("btc-usd", "UP")

        # Only 49 updates — still in warmup (total_obs < 50)
        for _ in range(49):
            strategy.update(s)

        signal = strategy.evaluate(s)
        assert signal.direction == "NEUTRAL"
        assert signal.confidence == 0.0
        assert signal.metadata == {"reason": "warmup"}

    def test_warmup_exact_boundary(self):
        """Tick 50 (warmup_ticks boundary) → is_ready=True, evaluate() returns valid signal."""
        strategy = MarkovStrategy(warmup_ticks=50)

        # 49 ticks of UP = not yet ready
        for _ in range(49):
            strategy.update(_state("btc-usd", "UP"))
        assert strategy.is_ready() is False

        # 50th tick crosses the threshold
        strategy.update(_state("btc-usd", "UP"))
        assert strategy.is_ready() is True

        # After 50 identical UP updates, _transition_counts[0][0] = 49
        # UP→UP is most probable = LONG
        s = _state("btc-usd", "UP")
        signal = strategy.evaluate(s)
        assert signal.direction == "LONG"
        assert signal.confidence > 0.0


class TestMarkovTransitionMatrix:
    def test_transition_counts_are_correct(self):
        """Known sequence UP, UP, DOWN, UP, UP → verify transition matrix."""
        strategy = MarkovStrategy(warmup_ticks=1)
        states = ["UP", "UP", "DOWN", "UP", "UP"]

        for label in states:
            strategy.update(_state("btc-usd", label))

        # Sequence breakdown:
        # 1st UP:   first state, _last_state becomes "UP", no transition yet
        # 2nd UP:   transition UP→UP, _transition_counts[0][0] = 1
        # 3rd DOWN: transition UP→DOWN, _transition_counts[0][1] = 1
        # 4th UP:   transition DOWN→UP, _transition_counts[1][0] = 1
        # 5th UP:   transition UP→UP, _transition_counts[0][0] = 2
        expected = [[2, 1, 0], [1, 0, 0], [0, 0, 0]]
        actual = strategy._transition_counts.tolist()
        assert actual == expected, f"Expected {expected}, got {actual}"

        assert strategy._state_counts.tolist() == [4, 1, 0]


class TestMarkovDeterminism:
    def test_two_instances_produce_identical_signals(self):
        """Two MarkovStrategy instances with same data → same signals."""
        states = []
        for i in range(55):
            label = "UP" if i % 3 == 0 else "DOWN" if i % 3 == 1 else "NEUTRAL"
            states.append(_state("btc-usd", label, datetime(2024, 1, 1, 12, 0, i)))

        s1 = MarkovStrategy(warmup_ticks=50)
        s2 = MarkovStrategy(warmup_ticks=50)

        signals_1 = []
        signals_2 = []

        for st in states:
            s1.update(st)
            s2.update(st)

        for st in states:
            sig1 = s1.evaluate(st)
            sig2 = s2.evaluate(st)
            signals_1.append(sig1)
            signals_2.append(sig2)

        for sig1, sig2 in zip(signals_1, signals_2):
            assert sig1.id == sig2.id
            assert sig1.direction == sig2.direction
            assert sig1.confidence == pytest.approx(sig2.confidence)


class TestMarkovArgmaxTiebreak:
    def test_tie_returns_first_index(self):
        """When two states have equal probability, argmax returns first (index 0 = UP)."""
        strategy = MarkovStrategy(warmup_ticks=1)

        # Build a row where UP=DOWN (both have 1 transition), NEUTRAL=0
        # UP -> UP: 1, UP -> DOWN: 1, UP -> NEUTRAL: 0
        strategy._transition_counts[0] = [1, 1, 0]
        strategy._total_obs = 2

        s = _state("btc-usd", "UP")
        signal = strategy.evaluate(s)
        # argmax on [0.5, 0.5, 0] → index 0 → UP → LONG
        assert signal.direction == "LONG"
        assert signal.confidence == 0.5


class TestMarkovNoTransitions:
    def test_no_transitions_from_current_returns_neutral(self):
        """If current state has no transitions recorded → NEUTRAL, confidence=0.0."""
        strategy = MarkovStrategy(warmup_ticks=1)

        strategy.update(_state("btc-usd", "UP"))
        strategy.update(_state("btc-usd", "DOWN"))

        # Now evaluate on NEUTRAL, which has never been a source of transitions
        s = _state("btc-usd", "NEUTRAL")
        signal = strategy.evaluate(s)
        assert signal.direction == "NEUTRAL"
        assert signal.confidence == 0.0
        assert signal.metadata["reason"] == "no_transitions_from_current_state"


class TestMarkovIsReady:
    def test_is_ready_false_before_warmup(self):
        """is_ready() returns False before warmup_ticks."""
        strategy = MarkovStrategy(warmup_ticks=10)
        for _ in range(9):
            strategy.update(_state("btc-usd", "UP"))
            assert strategy.is_ready() is False

    def test_is_ready_true_after_warmup(self):
        """is_ready() returns True after reaching warmup_ticks."""
        strategy = MarkovStrategy(warmup_ticks=10)
        for _ in range(10):
            strategy.update(_state("btc-usd", "UP"))
        assert strategy.is_ready() is True

    def test_is_ready_custom_warmup(self):
        """Custom warmup_ticks=3 works correctly."""
        strategy = MarkovStrategy(warmup_ticks=3)
        assert strategy.is_ready() is False
        for _ in range(3):
            strategy.update(_state("btc-usd", "UP"))
        assert strategy.is_ready() is True
