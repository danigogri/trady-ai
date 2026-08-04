"""Markov Persistence Engine — N×N transition matrix strategy with variants.

Provides:
    - MarkovPersistenceEngine: direction-prediction via Markov chain argmax
    - DirectionalPersistence: alias for semantic clarity (same state space)
    - VolatilityPersistence: volatility-regime classification (HIGH/LOW/STABLE)

The engine delegates state classification to an injected ``StateGenerator``,
operating exclusively on integer state indices. Without an explicit generator,
defaults to ``DirectionalStateGenerator(3)`` for backward compatibility.
"""

import json
import warnings
from decimal import Decimal
from typing import Any

import numpy as np
import sqlite_utils

from trady_ai.core.models import MarketInput, MarketState, Signal
from trady_ai.strategies.base import StrategyBase
from trady_ai.strategies.markov.state_generator import (
    DirectionalStateGenerator,
    StateGenerator,
)

# ── Module-level registry state (preserved for backward compat imports) ──
# These constants are no longer used internally. They remain exported so that
# external code referencing them does not break. New code should use
# StateGenerator instances instead.

STATE_INDEX: dict[str, int] = {"UP": 0, "DOWN": 1, "NEUTRAL": 2}
INDEX_STATE: dict[int, str] = {0: "UP", 1: "DOWN", 2: "NEUTRAL"}
DIRECTION_MAP: dict[str, str] = {"UP": "LONG", "DOWN": "SHORT", "NEUTRAL": "NEUTRAL"}

VOLATILITY_INDEX: dict[str, int] = {"HIGH": 0, "LOW": 1, "STABLE": 2}
VOLATILITY_INDEX_STATE: dict[int, str] = {0: "HIGH", 1: "LOW", 2: "STABLE"}
VOLATILITY_DIR_MAP: dict[str, str] = {"HIGH": "SHORT", "LOW": "LONG", "STABLE": "NEUTRAL"}


class MarkovPersistenceEngine(StrategyBase):
    """N×N Markov transition matrix strategy for state prediction.

    Delegates state classification to an injected ``StateGenerator``.
    The engine operates on integer state indices only — no semantic labels.

    Defaults to ``DirectionalStateGenerator(3)`` for backward compatibility
    with the original 3-state implementation.
    """

    def __init__(
        self,
        warmup_ticks: int = 50,
        threshold_pct: float = 0.001,
        state_generator: StateGenerator | None = None,
    ) -> None:
        self._generator = state_generator or DirectionalStateGenerator(
            threshold_pct=threshold_pct
        )
        s = self._generator.state_count
        self._transition_counts: np.ndarray = np.zeros((s, s), dtype=np.int64)
        self._state_counts: np.ndarray = np.zeros(s, dtype=np.int64)
        self._total_obs: int = 0
        self._warmup_ticks: int = warmup_ticks
        self._threshold_pct: float = threshold_pct
        self._last_state_idx: int | None = None

    # ── properties ────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "markov_persistence"

    # ── public interface ──────────────────────────────────────────────

    def is_ready(self) -> bool:
        """Return True when enough observations have been accumulated."""
        return self._total_obs >= self._warmup_ticks

    def parameters(self) -> dict[str, Any]:
        """Return strategy configuration parameters."""
        return {
            "warmup_ticks": self._warmup_ticks,
            "threshold_pct": self._threshold_pct,
        }

    # ── lifecycle hooks ─────────────────────────────────────────────

    @staticmethod
    def _market_input_from_state(state: MarketState) -> MarketInput:
        """Build a MarketInput from a MarketState for generator classification."""
        return MarketInput(
            timestamp=state.timestamp,
            market_id=state.market_id,
            price=state.price,
            volume=state.volume,
            source=state.source,
        )

    def on_update(self, state: MarketState) -> None:
        """Classify the market state via generator and increment transition counters."""
        self._total_obs += 1
        current_idx = self._generator.classify_from_label(state.state)
        self._state_counts[current_idx] += 1

        if self._last_state_idx is not None:
            self._transition_counts[self._last_state_idx][current_idx] += 1

        self._last_state_idx = current_idx

    def on_evaluate(self, state: MarketState) -> Signal:
        """Compute transition probabilities and return the best signal.

        Returns NEUTRAL/0.0 when the current state row has zero transitions.
        """
        current_idx = self._generator.classify_from_label(state.state)
        row = self._transition_counts[current_idx]

        if row.sum() == 0:
            return Signal(
                timestamp=state.timestamp,
                market_id=state.market_id,
                direction="NEUTRAL",
                confidence=0.0,
                strategy_name=self.name,
                metadata={"reason": "no_transitions_from_current_state"},
            )

        probs = row / row.sum()
        best_idx = int(np.argmax(probs))
        best_label = self._generator.state_labels[best_idx]
        direction = self._generator.signal_for_state(best_idx)
        confidence = float(probs[best_idx])

        return Signal(
            timestamp=state.timestamp,
            market_id=state.market_id,
            direction=direction,
            confidence=confidence,
            strategy_name=self.name,
            metadata={
                "probabilities": probs.tolist(),
                "state_label": best_label,
            },
        )

    def on_snapshot(self) -> dict[str, Any]:
        """Return serializable snapshot of internal state."""
        return {
            "strategy_name": self.name,
            "transition_counts": self._transition_counts.tolist(),
            "state_counts": self._state_counts.tolist(),
            "total_obs": self._total_obs,
            "last_state_idx": self._last_state_idx,
            "warmup_ticks": self._warmup_ticks,
            "threshold_pct": self._threshold_pct,
            "state_space_size": self._generator.state_count,
            "state_generator": self._generator.__class__.__name__,
        }

    # ── persistence: snapshot / restore ──────────────────────────────

    def snapshot(self, domain: str, db: sqlite_utils.Database) -> dict[str, Any]:
        """Persist current strategy state to the strategy_snapshots table.

        .. deprecated::
            Use ``on_snapshot()`` instead. This method emits a
            ``DeprecationWarning`` and returns the snapshot data dict
            without writing to the database. Snapshot persistence is
            now handled by the execution engine and reflection engine.

        Args:
            domain: Execution domain (set by registry).
            db:   sqlite-utils Database instance.

        Returns:
            dict[str, Any]: Snapshot data from ``on_snapshot()``.
        """
        warnings.warn(
            "snapshot() is deprecated; use on_snapshot() instead. "
            "Persistence is handled by the execution/reflection engine.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.on_snapshot()

    @classmethod
    def restore(
        cls, domain: str, name: str, db: sqlite_utils.Database
    ) -> "MarkovPersistenceEngine":
        """Reconstruct an engine from the latest DB snapshot.

        Args:
            domain: Execution domain.
            name:   Strategy name to restore.
            db:     sqlite-utils Database instance.

        Returns:
            A new MarkovPersistenceEngine (or subclass) instance with
            identical transition matrix and configuration.

        Raises:
            RuntimeError: If no snapshot exists for (domain, name).
            ValueError:   If stored JSON data is corrupt.
        """
        from trady_ai.core.persistence import load_latest_snapshot

        data = load_latest_snapshot(db, domain, name)
        if data is None:
            raise RuntimeError(f"No snapshot found for {domain}/{name}")

        try:
            trans = json.loads(data["transition_counts"])
            state_c = json.loads(data["state_counts"])
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Corrupt transition_counts in snapshot for {domain}/{name}: {e}"
            ) from e

        engine = cls(
            warmup_ticks=int(data["warmup_ticks"]),
            threshold_pct=float(data["threshold_pct"]),
        )
        engine._transition_counts = np.array(trans, dtype=np.int64)
        engine._state_counts = np.array(state_c, dtype=np.int64)
        engine._total_obs = int(np.sum(engine._state_counts))
        engine._last_state_idx = None  # Not stored in snapshot schema
        return engine


class DirectionalPersistence(MarkovPersistenceEngine):
    """Directional persistence — same state space as base class.

    Exists for semantic clarity: communicates intent that this strategy
    predicts price direction (LONG/SHORT/NEUTRAL) via Markov persistence.
    Functionally identical to MarkovPersistenceEngine.
    """

    @property
    def name(self) -> str:
        return "directional_persistence"


class VolatilityPersistence(MarkovPersistenceEngine):
    """Volatility persistence — classifies HIGH/LOW/STABLE volatility regime.

    Uses an injected ``VolatilityStateGenerator`` to classify the volatility
    regime from a sliding price window.
    """

    def __init__(
        self,
        warmup_ticks: int = 50,
        threshold_pct: float = 0.001,
        volatility_window: int = 20,
        state_generator: StateGenerator | None = None,
    ) -> None:
        if state_generator is None:
            from trady_ai.strategies.markov.state_generator import (
                VolatilityStateGenerator,
            )

            state_generator = VolatilityStateGenerator(
                threshold_pct=threshold_pct,
                volatility_window=volatility_window,
            )
        super().__init__(
            warmup_ticks=warmup_ticks,
            threshold_pct=threshold_pct,
            state_generator=state_generator,
        )
        self._volatility_window: int = volatility_window
        self._price_history: list[Decimal] = []

    @property
    def name(self) -> str:
        return "volatility_persistence"

    # ── backward-compat volatility classification ──────────────────

    def _classify_volatility(self) -> str:
        """Classify current volatility regime from price history (preserved for backward compat).

        Returns:
            One of ``"HIGH"``, ``"LOW"``, or ``"STABLE"``.

        Raises:
            TypeError: if no price data is available.
        """
        if not self._price_history:
            raise TypeError("No price data available for volatility classification")

        if len(self._price_history) < 2:
            return "STABLE"

        prices = [float(p) for p in self._price_history]
        min_price = min(prices)

        if min_price == 0.0:
            return "STABLE"

        range_pct = (max(prices) - min_price) / min_price

        if range_pct == 0.0:
            return "STABLE"
        if range_pct > self._threshold_pct:
            return "HIGH"
        if range_pct < self._threshold_pct * 0.5:
            return "LOW"
        return "STABLE"

    # ── overridden lifecycle hooks ──────────────────────────────────

    def on_update(self, state: MarketState) -> None:
        """Track price and update transition counts from volatility state."""
        self._price_history.append(state.price)
        if len(self._price_history) > self._volatility_window:
            self._price_history.pop(0)

        vol_state = self._classify_volatility()
        self._total_obs += 1
        current_idx = self._generator.classify_from_label(vol_state)
        self._state_counts[current_idx] += 1

        if self._last_state_idx is not None:
            self._transition_counts[self._last_state_idx][current_idx] += 1

        self._last_state_idx = current_idx

    def on_evaluate(self, state: MarketState) -> Signal:
        """Generate a signal based on volatility transition probabilities."""
        if not self._price_history:
            raise TypeError("No price data available for volatility classification")
        vol_state = self._classify_volatility()
        current_idx = self._generator.classify_from_label(vol_state)
        row = self._transition_counts[current_idx]

        if row.sum() == 0:
            return Signal(
                timestamp=state.timestamp,
                market_id=state.market_id,
                direction="NEUTRAL",
                confidence=0.0,
                strategy_name=self.name,
                metadata={"reason": "no_transitions_from_current_state"},
            )

        probs = row / row.sum()
        best_idx = int(np.argmax(probs))
        direction = self._generator.signal_for_state(best_idx)
        confidence = float(probs[best_idx])

        return Signal(
            timestamp=state.timestamp,
            market_id=state.market_id,
            direction=direction,
            confidence=confidence,
            strategy_name=self.name,
            metadata={
                "probabilities": probs.tolist(),
                "volatility_state": vol_state,
            },
        )
