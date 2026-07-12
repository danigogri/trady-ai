"""SignalQualityAnalyzer — signal accuracy and confidence calibration.

Stateless analyzer that queries signals, measures how many resulted in
trades (signal_accuracy), computes average confidence, and performs
confidence calibration binning.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlite_utils

from trady_ai.core.persistence import query_signals_by_time_range
from trady_ai.reflection.models import SignalQualityReport


class SignalQualityAnalyzer:
    """Analyzes signal quality within a time range.

    Determines how many signals produced corresponding trades, computes
    aggregate confidence metrics, and bins signals by confidence to
    measure calibration (predicted confidence vs actual win rate).
    Fully deterministic with ORDER BY ASC.
    """

    # Confidence threshold for high vs low calibration bins (Phase 4)
    _CONFIDENCE_THRESHOLD: float = 0.7

    def analyze(
        self,
        db: sqlite_utils.Database,
        domain: str,
        start: str,
        end: str,
    ) -> SignalQualityReport:
        """Compute signal quality metrics for the given time range.

        Args:
            db: Database instance.
            domain: Market domain (e.g. ``"PM-5M"``).
            start: ISO-8601 start timestamp (inclusive).
            end: ISO-8601 end timestamp (inclusive).

        Returns:
            SignalQualityReport with computed metrics. Zeroed when no signals
            exist in the time range.
        """
        signals = query_signals_by_time_range(db, start, end)
        total_signals = len(signals)

        if total_signals == 0:
            return SignalQualityReport(
                domain=domain,
                period_start=datetime.fromisoformat(start),
                period_end=datetime.fromisoformat(end),
                total_signals=0,
                signals_with_trades=0,
                signal_accuracy=0.0,
                avg_confidence=0.0,
                confidence_bins={
                    "high": {"count": 0.0, "winning": 0.0, "win_rate": 0.0},
                    "low": {"count": 0.0, "winning": 0.0, "win_rate": 0.0},
                },
            )

        # Count how many signals have at least one corresponding trade
        signal_ids = [s["id"] for s in signals]
        signals_with_trades = self._count_signals_with_trades(db, signal_ids)

        # Average confidence
        total_confidence = sum(float(s["confidence"]) for s in signals)
        avg_confidence = total_confidence / total_signals

        signal_accuracy = signals_with_trades / total_signals

        # Confidence calibration: 2 bins with threshold 0.7
        confidence_bins = self._compute_confidence_bins(db, signals)

        return SignalQualityReport(
            domain=domain,
            period_start=datetime.fromisoformat(start),
            period_end=datetime.fromisoformat(end),
            total_signals=total_signals,
            signals_with_trades=signals_with_trades,
            signal_accuracy=signal_accuracy,
            avg_confidence=avg_confidence,
            confidence_bins=confidence_bins,
        )

    @staticmethod
    def _count_signals_with_trades(
        db: sqlite_utils.Database, signal_ids: list[str]
    ) -> int:
        """Count how many of the given signal_ids have trades."""
        if not signal_ids:
            return 0
        placeholders = ",".join("?" for _ in signal_ids)
        rows = list(
            db.query(
                f"SELECT DISTINCT signal_id FROM trades WHERE signal_id IN ({placeholders})",
                signal_ids,
            )
        )
        return len(rows)

    @staticmethod
    def _compute_confidence_bins(
        db: sqlite_utils.Database,
        signals: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """Bin signals by confidence and compute actual win rates.

        Two bins: high-confidence (>= 0.7) and low-confidence (< 0.7).
        A signal is "winning" if it has a trade whose position pnl > 0.

        Returns:
            Dict with keys "high" and "low", each containing count, winning,
            and win_rate as floats.
        """
        threshold = SignalQualityAnalyzer._CONFIDENCE_THRESHOLD

        high_ids = [s["id"] for s in signals if float(s["confidence"]) >= threshold]
        low_ids = [s["id"] for s in signals if float(s["confidence"]) < threshold]

        high_winning = SignalQualityAnalyzer._count_winning_signals(db, high_ids)
        low_winning = SignalQualityAnalyzer._count_winning_signals(db, low_ids)

        return {
            "high": {
                "count": float(len(high_ids)),
                "winning": float(high_winning),
                "win_rate": float(high_winning / len(high_ids)) if high_ids else 0.0,
            },
            "low": {
                "count": float(len(low_ids)),
                "winning": float(low_winning),
                "win_rate": float(low_winning / len(low_ids)) if low_ids else 0.0,
            },
        }

    @staticmethod
    def _count_winning_signals(
        db: sqlite_utils.Database, signal_ids: list[str]
    ) -> int:
        """Count how many signals have at least one profitable trade.

        A signal is "winning" if it has a trade whose position pnl > 0.
        """
        if not signal_ids:
            return 0
        placeholders = ",".join("?" for _ in signal_ids)
        rows = list(
            db.query(
                "SELECT DISTINCT t.signal_id FROM trades t "
                "JOIN positions p ON t.position_id = p.id "
                f"WHERE t.signal_id IN ({placeholders}) "
                "AND CAST(p.pnl AS REAL) > 0.0",
                signal_ids,
            )
        )
        return len(rows)
