from uuid import NAMESPACE_URL, uuid5

import numpy as np

from trady_ai.core.models import MarketState, Signal
from trady_ai.core.signal_strategy import SignalStrategy

STATE_INDEX = {"UP": 0, "DOWN": 1, "NEUTRAL": 2}
INDEX_STATE = {0: "UP", 1: "DOWN", 2: "NEUTRAL"}
DIRECTION_MAP = {"UP": "LONG", "DOWN": "SHORT", "NEUTRAL": "NEUTRAL"}


class MarkovStrategy(SignalStrategy):
    """Concrete SignalStrategy using Markov Persistence with a 3×3 transition matrix.

    Tracks state transitions via numpy int64 counters. On evaluate(), computes
    conditional probabilities from the current state row and picks the most likely
    next state via np.argmax (deterministic on ties — returns first index).
    Cold-starts with NEUTRAL signals until warmup_ticks observations are reached.
    """

    def __init__(self, warmup_ticks: int = 50, threshold_pct: float = 0.001):
        self._transition_counts = np.zeros((3, 3), dtype=np.int64)
        self._state_counts = np.zeros(3, dtype=np.int64)
        self._total_obs = 0
        self._warmup_ticks = warmup_ticks
        self._threshold_pct = threshold_pct
        self._last_state: str | None = None

    @property
    def name(self) -> str:
        return "markov_persistence"

    def update(self, state: MarketState) -> None:
        self._total_obs += 1
        current_idx = STATE_INDEX[state.state]
        self._state_counts[current_idx] += 1

        if self._last_state is not None:
            prev_idx = STATE_INDEX[self._last_state]
            self._transition_counts[prev_idx][current_idx] += 1

        self._last_state = state.state

    def evaluate(self, state: MarketState) -> Signal:
        if not self.is_ready():
            return Signal(
                id=uuid5(NAMESPACE_URL, f"{self.name}:{state.market_id}:{state.timestamp.isoformat()}"),
                timestamp=state.timestamp,
                market_id=state.market_id,
                direction="NEUTRAL",
                confidence=0.0,
                strategy_name=self.name,
                metadata={"reason": "warmup"},
            )

        current_idx = STATE_INDEX[state.state]
        row = self._transition_counts[current_idx]

        if row.sum() == 0:
            return Signal(
                id=uuid5(NAMESPACE_URL, f"{self.name}:{state.market_id}:{state.timestamp.isoformat()}"),
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
            id=uuid5(NAMESPACE_URL, f"{self.name}:{state.market_id}:{state.timestamp.isoformat()}"),
            timestamp=state.timestamp,
            market_id=state.market_id,
            direction=direction,
            confidence=confidence,
            strategy_name=self.name,
            metadata={"probabilities": probs.tolist()},
        )

    def is_ready(self) -> bool:
        return self._total_obs >= self._warmup_ticks
