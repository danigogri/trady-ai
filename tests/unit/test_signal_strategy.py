from datetime import datetime
from decimal import Decimal

import pytest

from trady_ai.core.models import MarketState, Signal
from trady_ai.core.signal_strategy import SignalStrategy


class TestSignalStrategy:
    def test_cannot_instantiate_abc(self):
        """SignalStrategy() raises TypeError since it has abstract methods."""
        with pytest.raises(TypeError):
            SignalStrategy()  # type: ignore

    def test_concrete_implementation_passes_interface(self):
        """A minimal concrete implementation can be instantiated and passes the interface."""

        class DummyStrategy(SignalStrategy):
            @property
            def name(self) -> str:
                return "dummy"

            def evaluate(self, state: MarketState) -> Signal:
                return Signal(
                    timestamp=state.timestamp,
                    market_id=state.market_id,
                    direction="NEUTRAL",
                    confidence=0.0,
                    strategy_name=self.name,
                )

            def update(self, state: MarketState) -> None:
                pass

            def is_ready(self) -> bool:
                return True

        strategy = DummyStrategy()
        assert strategy.name == "dummy"
        assert strategy.is_ready() is True

        state = MarketState(
            market_id="btc-usd",
            timestamp=datetime(2024, 1, 1),
            price=Decimal("100.00"),
            volume=Decimal("1000"),
            state="UP",
        )
        signal = strategy.evaluate(state)
        assert signal.direction == "NEUTRAL"
        assert signal.confidence == 0.0
        assert signal.strategy_name == "dummy"
