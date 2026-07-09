from abc import ABC, abstractmethod

from trady_ai.core.models import MarketState, Signal


class SignalStrategy(ABC):
    """Abstract base for all signal generation strategies.

    The engine depends on this abstraction — NEVER on concrete strategies directly.
    Every concrete implementation MUST guarantee deterministic behaviour:
    same internal state + same input → same output for evaluate() and update().
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy name. Used in UUID generation and logging."""
        ...

    @abstractmethod
    def evaluate(self, state: MarketState) -> Signal:
        """Generate a signal based on current market state.

        If is_ready() == False, MUST return Signal(direction="NEUTRAL", confidence=0.0).
        """
        ...

    @abstractmethod
    def update(self, state: MarketState) -> None:
        """Update internal strategy state with a new observation.

        MUST be called before evaluate() for each tick.
        """
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True if the strategy has enough observations for valid signals."""
        ...
