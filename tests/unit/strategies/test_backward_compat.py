"""Tests for backward-compatible MarkovStrategy re-export.

Verifies that the legacy import path resolves to the migrated
MarkovPersistenceEngine with identical constructor signature and
correct inheritance.
"""

from trady_ai.core.markov_strategy import MarkovStrategy
from trady_ai.core.signal_strategy import SignalStrategy
from trady_ai.strategies.base import StrategyBase
from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine


class TestBackwardCompat:
    """MarkovStrategy resolves to MarkovPersistenceEngine via re-export."""

    def test_resolves_to_markov_persistence_engine(self):
        """MarkovStrategy IS MarkovPersistenceEngine (same class)."""
        assert MarkovStrategy is MarkovPersistenceEngine

    def test_isinstance_strategy_base(self):
        """MarkovStrategy() is-a StrategyBase."""
        assert isinstance(MarkovStrategy(), StrategyBase)

    def test_isinstance_signal_strategy(self):
        """MarkovStrategy() is-a SignalStrategy (LSP)."""
        assert isinstance(MarkovStrategy(), SignalStrategy)

    def test_constructor_signature_preserved(self):
        """MarkovStrategy(warmup_ticks=30, threshold_pct=0.002) works."""
        s = MarkovStrategy(warmup_ticks=30, threshold_pct=0.002)
        params = s.parameters()
        assert params["warmup_ticks"] == 30
        assert params["threshold_pct"] == 0.002

    def test_default_constructor(self):
        """Default constructor warmup_ticks=50, threshold_pct=0.001."""
        s = MarkovStrategy()
        params = s.parameters()
        assert params["warmup_ticks"] == 50
        assert params["threshold_pct"] == 0.001
