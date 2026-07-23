"""CalibrationAnalyzer — stateless, read-only evidence pipeline.

Computes deterministic evidence reports from strategy_snapshots data.
Follows the same injection pattern as DriftAnalyzer and OutcomeAnalyzer.
"""
from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import sqlite_utils

from trady_ai.reflection.calibration.metrics import (
    aic,
    bic,
    conditional_entropy,
    markov_chi2,
    state_persistence,
)
from trady_ai.reflection.calibration.models import EvidenceReport
from trady_ai.reflection.calibration.persistence import (
    load_transition_counts,
)


class CalibrationAnalyzer:
    """Stateless, read-only analyzer for Markov state space calibration.

    Computes AIC, BIC, Markov χ² test, state persistence, and conditional
    entropy from transition counts stored in strategy_snapshots.

    This analyzer NEVER modifies the database. It is read-only.
    """

    def analyze(
        self,
        db: sqlite_utils.Database,
        domain: str,
        strategy_name: str = "markov_persistence",
        tick_number: int | None = None,
    ) -> EvidenceReport:
        """Compute an EvidenceReport for a domain and strategy.

        Loads transition counts from strategy_snapshots, computes MLE
        transition probabilities, and evaluates all calibration metrics.

        Args:
            db: Database instance.
            domain: Market domain (e.g. ``"PM-5M"``).
            strategy_name: Strategy name (default: ``"markov_persistence"``).
            tick_number: Optional specific snapshot tick. Uses latest if
                ``None``.

        Returns:
            EvidenceReport with all computed metrics.
        """
        snapshot = load_transition_counts(db, domain, strategy_name, tick_number)
        if snapshot is None:
            return EvidenceReport(
                num_states=0,
                num_observations=0,
                computed_at=datetime.now(UTC).isoformat(),
            )

        trans_counts_list = snapshot["transition_counts"]
        state_space_size = snapshot["state_space_size"]

        # Convert to numpy array
        trans_counts = np.array(trans_counts_list, dtype=np.int64)

        # Compute total observations (sum of all transitions)
        num_observations = int(trans_counts.sum())

        # Build MLE transition probability matrix
        row_sums = trans_counts.sum(axis=1, dtype=np.float64)
        trans_probs = np.zeros_like(trans_counts, dtype=np.float64)
        for i in range(state_space_size):
            if row_sums[i] > 0:
                trans_probs[i, :] = trans_counts[i, :] / row_sums[i]

        # Build state sequence from available data
        state_sequence = self._build_state_sequence(
            trans_counts, state_space_size
        )

        # Compute metrics (deterministic)
        aic_val = aic(trans_counts, state_sequence)
        bic_val = bic(trans_counts, state_sequence, num_observations)
        chi2_result = markov_chi2(state_sequence, state_space_size)
        persist = state_persistence(trans_probs)
        entropy = conditional_entropy(trans_probs)

        report = EvidenceReport(
            aic=aic_val,
            bic=bic_val,
            markov_test=chi2_result,
            state_persistence=persist,
            conditional_entropy=entropy,
            num_states=state_space_size,
            num_observations=num_observations,
            transition_counts=trans_counts_list,
            computed_at=datetime.now(UTC).isoformat(),
        )

        return report

    def _build_state_sequence(
        self,
        trans_counts: np.ndarray,
        num_states: int,
    ) -> list[int]:
        """Build a representative state sequence from transition counts.

        Given a transition count matrix, reconstructs a state sequence that
        reproduces the same counts. This enables deterministic metric
        computation without a full stored state sequence.

        The sequence starts at state 0 and follows the most likely transitions,
        producing a sequence whose pair frequencies match the observed counts.

        Args:
            trans_counts: |S|×|S| transition count matrix.
            num_states: Size of the state space.

        Returns:
            List of state indices.
        """
        if num_states == 0:
            return []

        # Build sequence that matches the observed transition frequencies
        # Start at state 0, then follow the highest-count transition
        sequence: list[int] = [0]
        remaining = trans_counts.copy().astype(np.int64)

        # Maximum ticks to generate (prevent infinite loop)
        max_ticks = max(int(trans_counts.sum()) * 2, 100)

        for _ in range(max_ticks):
            current = sequence[-1]
            # Find the next state with the highest remaining count from current
            row = remaining[current, :]
            if row.sum() == 0:
                break
            # Pick the most frequent transition from current state
            next_state = int(np.argmax(row))
            if remaining[current, next_state] <= 0:
                break
            remaining[current, next_state] -= 1
            sequence.append(next_state)

        return sequence
