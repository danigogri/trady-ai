"""Pluggable StateGenerator ABC and concrete implementations.

Provides:
    - StateGenerator: Abstract base class for state classification
    - DirectionalStateGenerator: wraps MarketStateTracker threshold logic (|S|=3)
    - VolatilityStateGenerator: wraps VolatilityPersistence._classify_volatility logic (|S|=3)
    - get_generator(): Factory function for named generators
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from trady_ai.core.models import MarketInput

# ── Registry ────────────────────────────────────────────────────────

_STATE_GENERATORS: dict[str, type["StateGenerator"]] = {}


def _register(name: str, cls: type["StateGenerator"]) -> None:
    """Register a StateGenerator class under a human-readable name."""
    _STATE_GENERATORS[name] = cls


def get_generator(name: str, state_space_size: int = 3, **kwargs: object) -> "StateGenerator":
    """Factory: return a configured StateGenerator instance by name.

    Args:
        name: Generator name (e.g. ``"directional"``, ``"volatility"``).
        state_space_size: Number of states (default 3). Must be >= 2.

    Returns:
        A configured StateGenerator instance.

    Raises:
        ValueError: If ``name`` is not registered, or ``state_space_size < 2``.
    """
    if state_space_size < 2:
        raise ValueError(
            f"state_space_size must be >= 2, got {state_space_size}"
        )
    cls = _STATE_GENERATORS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown state generator: {name!r}. "
            f"Available: {sorted(_STATE_GENERATORS)}"
        )
    if "state_space_size" in kwargs:
        del kwargs["state_space_size"]
    return cls(**kwargs)


# ── Abstract base ───────────────────────────────────────────────────


class StateGenerator(ABC):
    """Pluggable state classifier for N-state Markov engines.

    The engine operates exclusively on integer state indices.
    Subclasses implement ``classify()`` to map ``MarketInput`` → index,
    and provide ``state_count`` + ``state_labels`` for the state space.
    """

    generator_name: str = "unknown"

    @property
    @abstractmethod
    def state_count(self) -> int:
        """|S| — fixed number of states. MUST NOT change during lifetime."""
        ...

    @property
    @abstractmethod
    def state_labels(self) -> list[str]:
        """Human-readable labels, length == ``state_count``. Index i ↔ labels[i]."""
        ...

    @abstractmethod
    def classify(self, input: MarketInput) -> int:
        """Map a MarketInput to a state index ∈ [0, |S|-1].

        MUST be deterministic: same input + same internal state → same index.
        """
        ...

    # ── concrete helpers ────────────────────────────────────────────

    def classify_from_label(self, label: str) -> int:
        """Map a pre-classified label string to a state index.

        Used when the engine pipeline provides a ``MarketState`` whose
        ``state`` field already contains a classified label (e.g. from a
        ``MarketStateTracker``). The default implementation performs a
        linear lookup in ``state_labels``.

        Args:
            label: Classified state label (e.g. ``"UP"``, ``"DOWN"``).

        Returns:
            State index ∈ [0, |S|-1].

        Raises:
            ValueError: If ``label`` is not in ``state_labels``.
        """
        try:
            return self.state_labels.index(label)
        except ValueError:
            raise ValueError(
                f"Unknown label {label!r} for {self.generator_name} generator. "
                f"Valid: {self.state_labels}"
            )

    def label(self, index: int) -> str:
        """Return the human-readable label for a state index.

        Args:
            index: State index ∈ [0, |S|-1].

        Returns:
            Human-readable label string.

        Raises:
            IndexError: If ``index`` is outside [0, |S|-1].
        """
        if 0 <= index < self.state_count:
            return self.state_labels[index]
        raise IndexError(f"State index {index} out of range [0, {self.state_count - 1}]")

    def signal_for_state(self, index: int) -> str:
        """Return the trading signal direction for a state index.

        Base implementation returns ``"NEUTRAL"`` for all states.
        Subclasses should override for domain-specific mapping.

        Args:
            index: State index ∈ [0, |S|-1].

        Returns:
            ``"LONG"``, ``"SHORT"``, or ``"NEUTRAL"``.
        """
        return _default_signal(index)


def _default_signal(_index: int) -> str:
    """Default signal direction: always NEUTRAL."""
    return "NEUTRAL"


# ── DirectionalStateGenerator ───────────────────────────────────────


class DirectionalStateGenerator(StateGenerator):
    """Threshold-based UP/DOWN/NEUTRAL classifier (|S|=3).

    Wraps the same logic as ``MarketStateTracker.update()``:
    tracks the last price per market, computes change percentage,
    and compares against a threshold.
    """

    generator_name: str = "directional"
    state_count: int = 3
    state_labels: list[str] = ["UP", "DOWN", "NEUTRAL"]
    _SIGNAL_MAP: dict[int, str] = {0: "LONG", 1: "SHORT", 2: "NEUTRAL"}

    def __init__(self, threshold_pct: float = 0.001) -> None:
        self._threshold_pct = threshold_pct
        self._prices: dict[str, Decimal] = {}

    def classify(self, input: MarketInput) -> int:
        """Classify price direction relative to the previous tick.

        First tick for a market → NEUTRAL (index 2).
        """
        previous_price = self._prices.get(input.market_id)
        self._prices[input.market_id] = input.price

        if previous_price is None:
            return 2  # NEUTRAL

        change_pct = (input.price - previous_price) / previous_price
        threshold = Decimal(str(self._threshold_pct))

        if change_pct > threshold:
            return 0  # UP
        if change_pct < -threshold:
            return 1  # DOWN
        return 2  # NEUTRAL

    def signal_for_state(self, index: int) -> str:
        return self._SIGNAL_MAP[index]


_register("directional", DirectionalStateGenerator)


# ── VolatilityStateGenerator ────────────────────────────────────────


class VolatilityStateGenerator(StateGenerator):
    """Volatility-regime classifier (|S|=3).

    Wraps the same logic as ``VolatilityPersistence._classify_volatility()``:
    maintains a sliding price window and classifies the price range
    into HIGH / LOW / STABLE volatility regimes.
    """

    generator_name: str = "volatility"
    state_count: int = 3
    state_labels: list[str] = ["HIGH", "LOW", "STABLE"]
    _SIGNAL_MAP: dict[int, str] = {0: "SHORT", 1: "LONG", 2: "NEUTRAL"}

    def __init__(self, threshold_pct: float = 0.001, volatility_window: int = 20) -> None:
        self._threshold_pct = threshold_pct
        self._volatility_window = volatility_window
        self._price_history: list[Decimal] = []

    @staticmethod
    def _classify_price_list(
        prices: list[Decimal], threshold_pct: float
    ) -> int:
        """Classify a list of prices into a volatility index (pure function).

        Used internally and for backward-compatible ``_classify_volatility``.

        Args:
            prices: List of Decimal prices.
            threshold_pct: Threshold for volatility classification.

        Returns:
            0 (HIGH), 1 (LOW), or 2 (STABLE).

        Raises:
            TypeError: If ``prices`` is empty.
        """
        if not prices:
            raise TypeError("No price data available for volatility classification")

        if len(prices) < 2:
            return 2  # STABLE

        fprices = [float(p) for p in prices]
        min_price = min(fprices)

        if min_price == 0.0:
            return 2  # STABLE

        range_pct = (max(fprices) - min_price) / min_price

        if range_pct == 0.0:
            return 2  # STABLE
        if range_pct > threshold_pct:
            return 0  # HIGH
        if range_pct < threshold_pct * 0.5:
            return 1  # LOW
        return 2  # STABLE

    def classify(self, input: MarketInput) -> int:
        """Classify volatility regime from price history.

        The input price is appended to the sliding window before classification.
        First few ticks (fewer than 2 in history) return STABLE.
        """
        self._price_history.append(input.price)
        if len(self._price_history) > self._volatility_window:
            self._price_history.pop(0)

        return self._classify_price_list(self._price_history, self._threshold_pct)

    def signal_for_state(self, index: int) -> str:
        return self._SIGNAL_MAP[index]


_register("volatility", VolatilityStateGenerator)
