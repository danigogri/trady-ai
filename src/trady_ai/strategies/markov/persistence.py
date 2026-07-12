"""Markov Persistence Engine — 3×3 transition matrix strategy with variants.

Provides:
    - MarkovPersistenceEngine: direction-prediction via Markov chain argmax
    - DirectionalPersistence: alias for semantic clarity (same state space)
    - VolatilityPersistence: volatility-regime classification (HIGH/LOW/STABLE)
"""

import json
from decimal import Decimal
from typing import Any

import numpy as np
import sqlite_utils

from trady_ai.core.models import MarketState, Signal
from trady_ai.strategies.base import StrategyBase

# ── Directional state space (shared by MarkovPersistenceEngine and DirectionalPersistence) ──

STATE_INDEX: dict[str, int] = {"UP": 0, "DOWN": 1, "NEUTRAL": 2}
INDEX_STATE: dict[int, str] = {0: "UP", 1: "DOWN", 2: "NEUTRAL"}
DIRECTION_MAP: dict[str, str] = {"UP": "LONG", "DOWN": "SHORT", "NEUTRAL": "NEUTRAL"}

# ── Volatility state space (used by VolatilityPersistence) ──

VOLATILITY_INDEX: dict[str, int] = {"HIGH": 0, "LOW": 1, "STABLE": 2}
VOLATILITY_INDEX_STATE: dict[int, str] = {0: "HIGH", 1: "LOW", 2: "STABLE"}
VOLATILITY_DIR_MAP: dict[str, str] = {"HIGH": "SHORT", "LOW": "LONG", "STABLE": "NEUTRAL"}


class MarkovPersistenceEngine(StrategyBase):
    """3×3 Markov transition matrix strategy for direction prediction.

    Tracks state transitions via numpy int64 counters. On evaluate(), computes
    conditional probabilities from the current state row and picks the most likely
    next state via np.argmax (deterministic on ties — returns first index).
    Cold-starts with NEUTRAL signals until warmup_ticks observations are reached.
    """

    def __init__(self, warmup_ticks: int = 50, threshold_pct: float = 0.001) -> None:
        self._transition_counts: np.ndarray = np.zeros((3, 3), dtype=np.int64)
        self._state_counts: np.ndarray = np.zeros(3, dtype=np.int64)
        self._total_obs: int = 0
        self._warmup_ticks: int = warmup_ticks
        self._threshold_pct: float = threshold_pct
        self._last_state: str | None = None

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

    def on_update(self, state: MarketState) -> None:
        """Classify the market state and increment transition counters."""
        self._total_obs += 1
        current_idx = STATE_INDEX[state.state]
        self._state_counts[current_idx] += 1

        if self._last_state is not None:
            prev_idx = STATE_INDEX[self._last_state]
            self._transition_counts[prev_idx][current_idx] += 1

        self._last_state = state.state

    def on_evaluate(self, state: MarketState) -> Signal:
        """Compute transition probabilities and return the best signal.

        Returns NEUTRAL/0.0 when the current state row has zero transitions.
        """
        current_idx = STATE_INDEX[state.state]
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
        best_state = INDEX_STATE[best_idx]
        direction = DIRECTION_MAP[best_state]
        confidence = float(probs[best_idx])

        return Signal(
            timestamp=state.timestamp,
            market_id=state.market_id,
            direction=direction,
            confidence=confidence,
            strategy_name=self.name,
            metadata={"probabilities": probs.tolist()},
        )

    def on_snapshot(self) -> dict[str, Any]:
        """Return serializable snapshot of internal state."""
        return {
            "transition_counts": self._transition_counts.tolist(),
            "state_counts": self._state_counts.tolist(),
            "total_obs": self._total_obs,
            "last_state": self._last_state,
            "warmup_ticks": self._warmup_ticks,
            "threshold_pct": self._threshold_pct,
        }

    # ── persistence: snapshot / restore ──────────────────────────────

    def snapshot(self, domain: str, db: sqlite_utils.Database) -> None:
        """Persist current strategy state to the strategy_snapshots table.

        Delegates to on_snapshot() for serializable state, then calls
        persist_strategy_snapshot() to write to SQLite.

        Args:
            domain: Execution domain (set by registry).
            db:   sqlite-utils Database instance.
        """
        from trady_ai.core.persistence import persist_strategy_snapshot

        snap = self.on_snapshot()
        persist_strategy_snapshot(
            db=db,
            domain=domain,
            strategy_name=self.name,
            tick_number=snap["total_obs"],
            transition_counts=snap["transition_counts"],
            state_counts=snap["state_counts"],
            warmup_ticks=snap["warmup_ticks"],
            threshold_pct=str(snap["threshold_pct"]),
        )

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
        engine._last_state = None  # Not stored in snapshot schema
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

    Instead of using MarketState.state for classification, maintains an
    internal price history and computes volatility from the price range.
    The output provides a confidence adjustment factor with metadata
    describing the current volatility state.
    """

    def __init__(
        self,
        warmup_ticks: int = 50,
        threshold_pct: float = 0.001,
        volatility_window: int = 20,
    ) -> None:
        super().__init__(warmup_ticks, threshold_pct)
        self._volatility_window: int = volatility_window
        self._price_history: list[Decimal] = []

    @property
    def name(self) -> str:
        return "volatility_persistence"

    # ── volatility classification ───────────────────────────────────

    def _classify_volatility(self) -> str:
        """Classify current volatility regime from price history.

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
        """Append price to history and update transition counts from volatility state."""
        self._price_history.append(state.price)
        if len(self._price_history) > self._volatility_window:
            self._price_history.pop(0)

        vol_state = self._classify_volatility()

        self._total_obs += 1
        current_idx = VOLATILITY_INDEX[vol_state]
        self._state_counts[current_idx] += 1

        if self._last_state is not None:
            prev_idx = VOLATILITY_INDEX[self._last_state]
            self._transition_counts[prev_idx][current_idx] += 1

        self._last_state = vol_state

    def on_evaluate(self, state: MarketState) -> Signal:
        """Generate a signal based on volatility transition probabilities."""
        vol_state = self._classify_volatility()
        current_idx = VOLATILITY_INDEX[vol_state]
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
        best_state = VOLATILITY_INDEX_STATE[best_idx]
        direction = VOLATILITY_DIR_MAP[best_state]
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
