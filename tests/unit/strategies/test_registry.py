"""Tests for StrategyRegistry.

Covers:
- Singleton per (domain, name) key
- Cross-domain independence (same name, different domain → different instance)
- KeyError on unknown domain/name
- list() with and without domain filter
- reset() clears all instances and factories
- Factory is called lazily on first get()
- Domain is set by registry post-creation
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from trady_ai.core.models import MarketState, Signal
from trady_ai.strategies.base import StrategyBase
from trady_ai.strategies.registry import StrategyRegistry

# ---------------------------------------------------------------------------
# Helper: concrete strategy for registry tests
# ---------------------------------------------------------------------------


class _RegistryTestStrategy(StrategyBase):
    """Strategy used exclusively to test the registry."""

    _counter = 0  # class-level counter to detect new instances

    def __init__(self) -> None:
        super().__init__()
        _RegistryTestStrategy._counter += 1
        self._instance_id = _RegistryTestStrategy._counter

    @property
    def name(self) -> str:
        return "registry_test"

    @property
    def domain(self) -> str:
        return self._domain

    @domain.setter
    def domain(self, value: str) -> None:
        self._domain = value

    def is_ready(self) -> bool:
        return True

    def parameters(self) -> dict[str, Any]:
        return {"warmup_ticks": 10, "threshold_pct": 0.001}

    def on_evaluate(self, state: MarketState) -> Signal:
        return Signal(
            timestamp=state.timestamp,
            market_id=state.market_id,
            direction="NEUTRAL",
            confidence=0.0,
            strategy_name=self.name,
        )

    @property
    def instance_id(self) -> int:
        """Unique per-instance identifier (monotonically increasing)."""
        return self._instance_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def factory() -> Callable[[], _RegistryTestStrategy]:
    return _RegistryTestStrategy


@pytest.fixture
def registry() -> StrategyRegistry:
    return StrategyRegistry()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegistryRegistration:
    """register() stores factory without creating instances."""

    def test_register_does_not_create_instance(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("domain-a", "strat", factory)
        # list shows registration, but no instance created yet
        assert ("domain-a", "strat") in registry.list()


class TestRegistryLazyInstantiation:
    """Factory is called only on first get()."""

    def test_factory_not_called_on_register(self, registry: StrategyRegistry) -> None:
        mock = MagicMock()
        registry.register("dom", "s", mock)
        mock.assert_not_called()

    def test_factory_called_on_first_get(self, registry: StrategyRegistry) -> None:
        mock = MagicMock(return_value=_RegistryTestStrategy())
        registry.register("dom", "s", mock)
        registry.get("dom", "s")
        mock.assert_called_once()

    def test_factory_not_called_again_on_second_get(
        self, registry: StrategyRegistry
    ) -> None:
        mock = MagicMock(return_value=_RegistryTestStrategy())
        registry.register("dom", "s", mock)
        registry.get("dom", "s")
        registry.get("dom", "s")
        mock.assert_called_once()


class TestRegistrySingletonPerKey:
    """get() returns the same instance for the same (domain, name) key."""

    def test_same_instance_returned_on_second_get(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("domain-a", "strat", factory)
        first = registry.get("domain-a", "strat")
        second = registry.get("domain-a", "strat")
        assert first is second

    def test_different_domain_returns_different_instance(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("domain-a", "strat", factory)
        registry.register("domain-b", "strat", factory)
        a = registry.get("domain-a", "strat")
        b = registry.get("domain-b", "strat")
        assert a is not b
        assert a.domain == "domain-a"
        assert b.domain == "domain-b"


class TestRegistryKeyError:
    """get() raises KeyError for unknown strategies."""

    def test_unknown_domain_raises_key_error(
        self, registry: StrategyRegistry
    ) -> None:
        with pytest.raises(KeyError):
            registry.get("UNKNOWN", "foo")

    def test_unknown_name_raises_key_error(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("domain-a", "known", factory)
        with pytest.raises(KeyError):
            registry.get("domain-a", "unknown")


class TestRegistryList:
    """list() returns registered (domain, name) tuples."""

    def test_list_all(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("a", "x", factory)
        registry.register("a", "y", factory)
        registry.register("b", "z", factory)
        entries = registry.list()
        assert ("a", "x") in entries
        assert ("a", "y") in entries
        assert ("b", "z") in entries

    def test_list_filtered_by_domain(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("a", "x", factory)
        registry.register("a", "y", factory)
        registry.register("b", "z", factory)
        entries = registry.list(domain="a")
        assert entries == [("a", "x"), ("a", "y")]

    def test_list_unknown_domain_returns_empty(
        self, registry: StrategyRegistry
    ) -> None:
        assert registry.list(domain="nonexistent") == []

    def test_list_empty_registry(self, registry: StrategyRegistry) -> None:
        assert registry.list() == []


class TestRegistryReset:
    """reset() clears all instances and factories."""

    def test_reset_clears_instances(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("dom", "s", factory)
        registry.get("dom", "s")
        registry.reset()
        with pytest.raises(KeyError):
            registry.get("dom", "s")

    def test_reset_clears_factory_too(self, registry: StrategyRegistry) -> None:
        registry.register("dom", "s", _RegistryTestStrategy)
        registry.reset()
        assert registry.list() == []

    def test_reset_allows_new_registration(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("dom", "s", factory)
        registry.reset()
        registry.register("dom", "s", factory)
        instance = registry.get("dom", "s")
        assert instance is not None


class TestRegistryDomainAssignment:
    """Registry sets .domain on the instance after creation."""

    def test_domain_is_set_by_registry(
        self, registry: StrategyRegistry, factory: Callable[[], _RegistryTestStrategy]
    ) -> None:
        registry.register("PM-5M", "strat", factory)
        instance = registry.get("PM-5M", "strat")
        assert instance.domain == "PM-5M"
