"""StrategyBase — abstract base for all trading strategies.

Refines SignalStrategy with:
- Fail-fast input validation (TypeError on non-MarketState)
- Warmup guard (NEUTRAL signal when not ready)
- Lifecycle hooks (on_init, on_update, on_evaluate, on_snapshot)
- Domain property (set by registry post-creation)
- Isolation: no access to adapters, governance, or persistence
"""

from abc import ABC, abstractmethod
from typing import Any

from trady_ai.core.models import MarketState, Signal
from trady_ai.core.signal_strategy import SignalStrategy


class StrategyBase(SignalStrategy, ABC):
    """Abstract base for isolation-compliant strategy implementations.

    Provides concrete ``evaluate()`` and ``update()`` with input validation
    and warmup guard, then delegates to lifecycle hooks that subclasses
    override for domain-specific logic.

    Subclasses must implement:
        - ``name`` (from SignalStrategy)
        - ``is_ready`` (from SignalStrategy)
        - ``parameters()``
        - ``on_evaluate(state) -> Signal``

    Subclasses may optionally override:
        - ``domain`` (property; default read-write backed by ``_domain``)
        - ``on_init()``, ``on_update(state)``, ``on_snapshot()``
    """

    _domain: str = ""

    # ---- domain property (read-write) -----------------------------------

    @property
    def domain(self) -> str:
        """Execution domain this strategy belongs to.

        Set by the registry post-creation, NOT in the constructor.
        Subclasses may override to return a static value.
        """
        return self._domain

    @domain.setter
    def domain(self, value: str) -> None:
        self._domain = value

    # ---- abstract interface ---------------------------------------------

    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Return strategy parameters (e.g. warmup_ticks, threshold_pct)."""
        ...

    # ---- public interface with fail-fast guards -------------------------

    def update(self, state: MarketState) -> None:
        """Update internal state with a new observation.

        Raises:
            TypeError: if ``state`` is not a ``MarketState``.
        """
        if not isinstance(state, MarketState):
            raise TypeError(
                f"Strategy.update() requires MarketState, got {type(state).__name__}"
            )
        self.on_update(state)

    def evaluate(self, state: MarketState) -> Signal:
        """Produce a signal for the given market state.

        When ``is_ready()`` is ``False`` returns a warmup signal
        (NEUTRAL / confidence 0.0 / reason="warmup").

        Raises:
            TypeError: if ``state`` is not a ``MarketState``.
        """
        if not isinstance(state, MarketState):
            raise TypeError(
                f"Strategy.evaluate() requires MarketState, got {type(state).__name__}"
            )
        if not self.is_ready():
            return Signal(
                timestamp=state.timestamp,
                market_id=state.market_id,
                direction="NEUTRAL",
                confidence=0.0,
                strategy_name=self.name,
                metadata={"reason": "warmup"},
            )
        return self.on_evaluate(state)

    # ---- lifecycle hooks (override in subclasses) -----------------------

    def on_init(self) -> None:
        """Validate parameters after construction.

        Override to raise ``ValueError`` on invalid configuration.
        """
        return None

    def on_update(self, state: MarketState) -> None:
        """Process a market state observation.

        Called by ``update()`` after type validation passes.
        Default is a no-op.
        """

    def on_evaluate(self, state: MarketState) -> Signal:
        """Generate a signal from the current market state.

        Called by ``evaluate()`` when the strategy is ready.
        Subclasses MUST override this method.

        Raises:
            NotImplementedError: if not overridden in a subclass.
        """
        raise NotImplementedError("Subclasses must implement on_evaluate()")

    def on_snapshot(self) -> dict[str, Any]:
        """Return serializable snapshot data for persistence.

        Default returns empty dict. Override to include strategy state.
        """
        return {}
