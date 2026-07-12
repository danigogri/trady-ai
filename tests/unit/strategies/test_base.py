"""Tests for StrategyBase ABC.

Covers:
- ABC constraints (cannot instantiate, abstract methods enforced)
- Fail-fast on invalid input types (TypeError)
- Warmup Signal when not ready
- No adapter/governance imports in strategy code
- parameters() contract
- Lifecycle hooks contract
- Domain property set/get
"""

from abc import ABC
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from trady_ai.core.models import MarketState, Signal
from trady_ai.core.signal_strategy import SignalStrategy
from trady_ai.strategies.base import StrategyBase

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _market_state(**overrides: Any) -> MarketState:
    defaults: dict[str, Any] = dict(
        market_id="btc-usd",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        price=Decimal("100.00"),
        volume=Decimal("1000"),
        state="NEUTRAL",
    )
    defaults.update(overrides)
    return MarketState(**defaults)


class DummyStrategy(StrategyBase):
    """Minimal concrete StrategyBase subclass for testing."""

    def __init__(self) -> None:
        super().__init__()
        self._ready = True

    @property
    def name(self) -> str:
        return "dummy"

    def is_ready(self) -> bool:
        return self._ready

    def set_ready(self, value: bool) -> None:
        self._ready = value

    def parameters(self) -> dict[str, Any]:
        return {"warmup_ticks": 50, "threshold_pct": 0.001}

    def on_evaluate(self, state: MarketState) -> Signal:
        return Signal(
            timestamp=state.timestamp,
            market_id=state.market_id,
            direction="NEUTRAL",
            confidence=0.0,
            strategy_name=self.name,
        )


# ---------------------------------------------------------------------------
# ABC constraints
# ---------------------------------------------------------------------------


class TestStrategyBaseIsABC:
    """StrategyBase cannot be instantiated directly (abstract methods)."""

    def test_is_subclass_of_abc(self) -> None:
        assert issubclass(StrategyBase, ABC)

    def test_is_subclass_of_signal_strategy(self) -> None:
        assert issubclass(StrategyBase, SignalStrategy)

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            StrategyBase()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Concrete behaviour
# ---------------------------------------------------------------------------


class TestStrategyBaseBehaviour:
    """Behavioural tests using a concrete DummyStrategy."""

    @pytest.fixture
    def strategy(self) -> DummyStrategy:
        return DummyStrategy()

    @pytest.fixture
    def state(self) -> MarketState:
        return _market_state()

    # -- Type checking -----------------------------------------------------

    def test_update_non_market_state_raises_type_error(
        self, strategy: DummyStrategy
    ) -> None:
        with pytest.raises(TypeError, match="MarketState"):
            strategy.update("not a MarketState")  # type: ignore[arg-type]

    def test_evaluate_non_market_state_raises_type_error(
        self, strategy: DummyStrategy
    ) -> None:
        with pytest.raises(TypeError, match="MarketState"):
            strategy.evaluate("not a MarketState")  # type: ignore[arg-type]

    # -- Warmup ------------------------------------------------------------

    def test_evaluate_returns_warmup_signal_when_not_ready(
        self, strategy: DummyStrategy, state: MarketState
    ) -> None:
        strategy.set_ready(False)
        signal = strategy.evaluate(state)
        assert signal.direction == "NEUTRAL"
        assert signal.confidence == 0.0
        assert signal.metadata == {"reason": "warmup"}

    def test_evaluate_returns_warmup_signal_with_strategy_name(
        self, strategy: DummyStrategy, state: MarketState
    ) -> None:
        strategy.set_ready(False)
        signal = strategy.evaluate(state)
        assert signal.strategy_name == "dummy"

    # -- parameters() ------------------------------------------------------

    def test_parameters_returns_dict_with_expected_keys(
        self, strategy: DummyStrategy
    ) -> None:
        params = strategy.parameters()
        assert isinstance(params, dict)
        assert "warmup_ticks" in params
        assert "threshold_pct" in params

    # -- Domain property ---------------------------------------------------

    def test_domain_defaults_to_empty_string(self, strategy: DummyStrategy) -> None:
        assert strategy.domain == ""

    def test_domain_can_be_set_via_property(self, strategy: DummyStrategy) -> None:
        strategy.domain = "PM-5M"
        assert strategy.domain == "PM-5M"

    # -- Lifecycle hooks ---------------------------------------------------

    def test_lifecycle_hooks_exist(self, strategy: DummyStrategy) -> None:
        assert hasattr(strategy, "on_init")
        assert hasattr(strategy, "on_update")
        assert hasattr(strategy, "on_evaluate")
        assert hasattr(strategy, "on_snapshot")

    def test_on_snapshot_returns_dict(self, strategy: DummyStrategy) -> None:
        result = strategy.on_snapshot()
        assert isinstance(result, dict)

    # -- evaluate delegates to on_evaluate when ready ----------------------

    def test_evaluate_delegates_to_on_evaluate_when_ready(
        self, strategy: DummyStrategy, state: MarketState
    ) -> None:
        signal = strategy.evaluate(state)
        assert signal.strategy_name == "dummy"
        assert signal.market_id == state.market_id


# ---------------------------------------------------------------------------
# Isolation: no adapter / governance / persistence imports in strategy code
# ---------------------------------------------------------------------------


class TestStrategyBaseIsolation:
    """Verify no forbidden imports in strategy modules."""

    def test_no_adapter_or_governance_imports_in_base(self) -> None:
        import inspect

        import trady_ai.strategies.base as mod

        source = inspect.getsource(mod)
        forbidden = ["trady_ai.adapters", "trady_ai.governance"]
        for token in forbidden:
            assert token not in source, f"base.py must not import {token}"
