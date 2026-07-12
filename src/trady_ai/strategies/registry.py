"""StrategyRegistry — factory-backed registry for ``StrategyBase`` instances.

Provides singleton-per-key semantics: each ``(domain, name)`` pair yields
exactly one instance, created lazily on the first ``get()`` call.

Usage::

    registry = StrategyRegistry()
    registry.register("PM-5M", "markov_persistence", MarkovPersistenceEngine)
    strategy = registry.get("PM-5M", "markov_persistence")
    strategy.domain  # → "PM-5M" (set by registry)
"""

from collections.abc import Callable

from trady_ai.strategies.base import StrategyBase


class StrategyRegistry:
    """Manages strategy instances by ``(domain, name)`` keys.

    Instance variables (not class variables) so multiple registries can
    coexist with independent state.
    """

    def __init__(self) -> None:
        self._instances: dict[str, dict[str, StrategyBase]] = {}
        self._factories: dict[str, dict[str, Callable[[], StrategyBase]]] = {}

    def register(self, domain: str, name: str, factory: Callable[[], StrategyBase]) -> None:
        """Register a factory for a strategy key.

        The factory is NOT called until the first ``get()`` for this key.
        """
        if domain not in self._factories:
            self._factories[domain] = {}
        self._factories[domain][name] = factory

    def get(self, domain: str, name: str) -> StrategyBase:
        """Return the strategy instance for ``(domain, name)``.

        On first call, the registered factory is invoked, the instance's
        ``domain`` is set to the key domain, and the instance is cached.
        Subsequent calls return the same instance.

        Raises:
            KeyError: if no factory is registered for ``(domain, name)``.
        """
        # Guard: unknown domain or name
        if domain not in self._factories or name not in self._factories[domain]:
            raise KeyError(f"Unknown strategy: {domain}/{name}")

        # Lazy instantiation
        if domain not in self._instances:
            self._instances[domain] = {}
        if name not in self._instances[domain]:
            instance = self._factories[domain][name]()
            instance.domain = domain
            self._instances[domain][name] = instance

        return self._instances[domain][name]

    def list(self, domain: str | None = None) -> list[tuple[str, str]]:
        """List registered strategy keys.

        Args:
            domain: If provided, only keys for this domain are returned.

        Returns:
            List of ``(domain, name)`` tuples (empty if nothing registered).
        """
        if domain is not None:
            if domain not in self._factories:
                return []
            return [(domain, name) for name in sorted(self._factories[domain])]

        result: list[tuple[str, str]] = []
        for d in sorted(self._factories):
            for n in sorted(self._factories[d]):
                result.append((d, n))
        return result

    def reset(self) -> None:
        """Clear all cached instances AND registered factories."""
        self._instances.clear()
        self._factories.clear()
