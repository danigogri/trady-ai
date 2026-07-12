"""DriftAnalyzer — threshold-based drift detection for strategy behavior.

Stateless analyzer that compares two strategy snapshots (transition matrices)
and flags cells where the deviation exceeds a configurable threshold.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import sqlite_utils

from trady_ai.reflection.models import DriftEvent


class DriftAnalyzer:
    """Detects drift in strategy transition matrices.

    Compares transition_counts from two strategy_snapshots. When either both
    ``baseline_tick`` and ``comparison_tick`` are ``None``, the two most recent
    snapshots are used. Deterministic with fixed iteration order (3×3 range
    loops, never dict iteration).
    """

    def analyze(
        self,
        db: sqlite_utils.Database,
        strategy_id: str,
        domain: str,
        baseline_tick: int | None = None,
        comparison_tick: int | None = None,
        threshold: float = 0.15,
    ) -> list[DriftEvent]:
        """Detect drift events by comparing two strategy snapshots.

        Args:
            db: Database instance.
            strategy_id: Strategy identifier (maps to ``strategy_name``).
            domain: Market domain (e.g. ``"PM-5M"``).
            baseline_tick: Baseline snapshot tick. ``None`` for latest two.
            comparison_tick: Comparison snapshot tick. ``None`` for latest two.
            threshold: Deviation threshold as a fraction (default 0.15 = 15%).

        Returns:
            List of ``DriftEvent`` for each cell that exceeds the threshold.
            Empty list when no drift is detected or fewer than 2 snapshots
            exist.

        Raises:
            ValueError: If exactly one of ``baseline_tick`` or
                ``comparison_tick`` is provided (need both or neither).
        """
        # Validate tick args: both or neither
        has_baseline = baseline_tick is not None
        has_comparison = comparison_tick is not None
        if has_baseline != has_comparison:
            raise ValueError(
                "Must provide both baseline_tick and comparison_tick, or neither. "
                f"Got baseline_tick={baseline_tick!r}, comparison_tick={comparison_tick!r}"
            )

        # Fetch snapshots
        if has_baseline and has_comparison:
            # Both ticks provided — fetch specific snapshots
            assert baseline_tick is not None  # narrowed
            assert comparison_tick is not None
            snapshots = list(
                db.query(
                    "SELECT * FROM strategy_snapshots "
                    "WHERE strategy_name = ? AND domain = ? "
                    "AND tick_number IN (?, ?) "
                    "ORDER BY tick_number ASC",
                    [strategy_id, domain, baseline_tick, comparison_tick],
                )
            )
        else:
            # Fetch latest two snapshots
            snapshots = list(
                db.query(
                    "SELECT * FROM strategy_snapshots "
                    "WHERE strategy_name = ? AND domain = ? "
                    "ORDER BY tick_number DESC LIMIT 2",
                    [strategy_id, domain],
                )
            )

        if len(snapshots) < 2:
            return []

        # snapshots are ORDER BY tick_number ASC (explicit ticks) or
        # DESC LIMIT 2. Ensure chronological order: old → new.
        snap_a: dict[str, Any] = snapshots[0]
        snap_b: dict[str, Any] = snapshots[1]

        # Verify we have the right ordering
        if snap_a["tick_number"] > snap_b["tick_number"]:
            snap_a, snap_b = snap_b, snap_a

        # Parse transition matrices (JSON list-of-lists)
        trans_a = json.loads(snap_a["transition_counts"])
        trans_b = json.loads(snap_b["transition_counts"])

        detected_at = datetime.now(UTC)

        events: list[DriftEvent] = []
        # Fixed iteration order: 3x3 matrix, range loops (never dict iteration)
        for i in range(3):
            for j in range(3):
                baseline_count = float(trans_a[i][j])
                comparison_count = float(trans_b[i][j])
                denom = max(baseline_count, 1.0)
                deviation_pct = abs(comparison_count - baseline_count) / denom * 100.0

                if deviation_pct > threshold * 100.0:
                    events.append(
                        DriftEvent(
                            strategy_id=strategy_id,
                            domain=domain,
                            metric=f"transition_{i}_{j}",
                            previous_value=baseline_count,
                            current_value=comparison_count,
                            threshold=threshold,
                            deviation_pct=deviation_pct,
                            detected_at=detected_at,
                        )
                    )

        return events
