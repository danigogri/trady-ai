"""OutcomeAnalyzer — trade outcome analysis for a domain/time range.

Stateless analyzer that queries trades and computes win_rate, total PnL,
average PnL per trade, and maximum drawdown.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlite_utils

from trady_ai.core.persistence import query_trades_by_time_range
from trady_ai.reflection.models import OutcomeSummary


class OutcomeAnalyzer:
    """Analyzes trade outcomes within a time range.

    All calculations are deterministic using ORDER BY ASC and Decimal
    arithmetic for PnL values.
    """

    def analyze(
        self,
        db: sqlite_utils.Database,
        domain: str,
        start: str,
        end: str,
    ) -> OutcomeSummary:
        """Compute trade outcome statistics for the given time range.

        Args:
            db: Database instance.
            domain: Market domain (e.g. ``"PM-5M"``).
            start: ISO-8601 start timestamp (inclusive).
            end: ISO-8601 end timestamp (inclusive).

        Returns:
            OutcomeSummary with computed metrics. Zeroed when no trades exist
            in the time range.
        """
        trades = query_trades_by_time_range(db, start, end)
        total_trades = len(trades)

        if total_trades == 0:
            return OutcomeSummary(
                domain=domain,
                period_start=datetime.fromisoformat(start),
                period_end=datetime.fromisoformat(end),
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=Decimal("0"),
                avg_pnl_per_trade=Decimal("0"),
                max_drawdown=Decimal("0"),
            )

        # Collect unique position_ids to batch-load positions
        position_ids = [t["position_id"] for t in trades if t["position_id"] is not None]
        if not position_ids:
            return self._zeroed(domain, start, end)

        # Batch load positions for all CLOSE trades
        positions = self._load_positions(db, position_ids)
        pos_by_id: dict[str, dict[str, Any]] = {p["id"]: p for p in positions}

        # Extract PnL from CLOSE trades only (realized PnL)
        pnls: list[Decimal] = []
        close_trade_count = 0
        for t in trades:
            if t["action"] != "CLOSE":
                continue
            pos = pos_by_id.get(t["position_id"])
            if pos is None:
                continue
            pnl_str = pos.get("pnl")
            if pnl_str is None:
                continue
            try:
                pnl = Decimal(str(pnl_str))
            except Exception:
                continue
            pnls.append(pnl)
            close_trade_count += 1

        if close_trade_count == 0:
            return self._zeroed(domain, start, end)

        winning_trades = sum(1 for pnl in pnls if pnl > Decimal("0"))
        losing_trades = sum(1 for pnl in pnls if pnl <= Decimal("0"))
        total_pnl = sum(pnls, Decimal("0"))
        avg_pnl = total_pnl / Decimal(str(close_trade_count))
        win_rate = float(winning_trades) / float(close_trade_count)

        # Max drawdown: running PnL peak-to-trough
        running_pnl = Decimal("0")
        peak = Decimal("0")
        max_drawdown = Decimal("0")
        for pnl in pnls:
            running_pnl += pnl
            if running_pnl > peak:
                peak = running_pnl
            drawdown = peak - running_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return OutcomeSummary(
            domain=domain,
            period_start=datetime.fromisoformat(start),
            period_end=datetime.fromisoformat(end),
            total_trades=close_trade_count,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl_per_trade=avg_pnl,
            max_drawdown=max_drawdown,
        )

    def _zeroed(
        self, domain: str, start: str, end: str
    ) -> OutcomeSummary:
        """Return a zeroed OutcomeSummary for empty/no-PnL ranges."""
        return OutcomeSummary(
            domain=domain,
            period_start=datetime.fromisoformat(start),
            period_end=datetime.fromisoformat(end),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=Decimal("0"),
            avg_pnl_per_trade=Decimal("0"),
            max_drawdown=Decimal("0"),
        )

    @staticmethod
    def _load_positions(
        db: sqlite_utils.Database, position_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Batch-load positions by their IDs."""
        if not position_ids:
            return []
        placeholders = ",".join("?" for _ in position_ids)
        return list(
            db.query(
                f"SELECT * FROM positions WHERE id IN ({placeholders})",
                position_ids,
            )
        )
