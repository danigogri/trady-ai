"""Persistence helpers for the Reflection Systems module.

Provides save/query functions for reflection_reports, drift_events, proposals,
and reflection_config tables.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import sqlite_utils

from trady_ai.reflection.models import (
    DriftEvent,
    Proposal,
    ReflectionReport,
)


def _serialize_value(obj: Any) -> str:
    """Safety net for json.dumps default handler.

    _serialize_report_data() pre-converts all values to JSON-safe types,
    so this function should never be invoked in normal operation. It exists
    as a defensive guard against future fields that may contain Decimal
    or datetime values without explicit pre-serialization.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _serialize_report_data(report: ReflectionReport) -> str:
    """Serialize a ReflectionReport's structured data to JSON.

    Includes outcome_summary, signal_quality (with confidence_bins),
    drift_events, and proposals.
    """
    data: dict[str, Any] = {}

    if report.outcome_summary is not None:
        os = report.outcome_summary
        data["outcome_summary"] = {
            "domain": os.domain,
            "period_start": os.period_start.isoformat(),
            "period_end": os.period_end.isoformat(),
            "total_trades": os.total_trades,
            "winning_trades": os.winning_trades,
            "losing_trades": os.losing_trades,
            "win_rate": os.win_rate,
            "total_pnl": str(os.total_pnl),
            "avg_pnl_per_trade": str(os.avg_pnl_per_trade),
            "max_drawdown": str(os.max_drawdown),
        }

    if report.signal_quality is not None:
        sq = report.signal_quality
        data["signal_quality"] = {
            "domain": sq.domain,
            "period_start": sq.period_start.isoformat(),
            "period_end": sq.period_end.isoformat(),
            "total_signals": sq.total_signals,
            "signals_with_trades": sq.signals_with_trades,
            "signal_accuracy": sq.signal_accuracy,
            "avg_confidence": sq.avg_confidence,
            "confidence_bins": sq.confidence_bins,
        }

    data["drift_events"] = [
        {
            "strategy_id": e.strategy_id,
            "domain": e.domain,
            "metric": e.metric,
            "previous_value": e.previous_value,
            "current_value": e.current_value,
            "threshold": e.threshold,
            "deviation_pct": e.deviation_pct,
            "detected_at": e.detected_at.isoformat(),
        }
        for e in report.drift_events
    ]

    data["proposals"] = [
        {
            "strategy_id": p.strategy_id,
            "parameter_name": p.parameter_name,
            "current_value": p.current_value,
            "proposed_value": p.proposed_value,
            "range_min": p.range_min,
            "range_max": p.range_max,
            "justification": p.justification,
            "status": p.status,
            "created_at": p.created_at.isoformat(),
        }
        for p in report.proposals
    ]

    return json.dumps(data, default=_serialize_value)


def save_reflection_report(db: sqlite_utils.Database, report: ReflectionReport) -> int:
    """Save a ReflectionReport to the reflection_reports table.

    Args:
        db: Database instance.
        report: The report to persist.

    Returns:
        int: The auto-generated report ID.
    """
    report_data = _serialize_report_data(report)
    now = datetime.now(UTC).isoformat()
    cursor = db.execute(
        "INSERT INTO reflection_reports "
        "(scope, domain, mode, period_start, period_end, report_data, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            report.scope,
            report.domain,
            report.mode,
            report.period_start.isoformat(),
            report.period_end.isoformat(),
            report_data,
            now,
        ],
    )
    # lastrowid is guaranteed non-None after a successful INSERT
    return int(cursor.lastrowid)


def save_drift_events(db: sqlite_utils.Database, events: list[DriftEvent]) -> None:
    """Save drift events to the drift_events table.

    Args:
        db: Database instance.
        events: List of DriftEvent objects to persist.
    """
    for event in events:
        db.execute(
            "INSERT INTO drift_events "
            "(strategy_id, domain, metric, previous_value, current_value, "
            "threshold, deviation_pct, detected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                event.strategy_id,
                event.domain,
                event.metric,
                event.previous_value,
                event.current_value,
                event.threshold,
                event.deviation_pct,
                event.detected_at.isoformat(),
            ],
        )


def save_proposals(db: sqlite_utils.Database, proposals: list[Proposal]) -> None:
    """Save proposals to the proposals table.

    Args:
        db: Database instance.
        proposals: List of Proposal objects to persist.
    """
    for proposal in proposals:
        db.execute(
            "INSERT INTO proposals "
            "(strategy_id, parameter_name, current_value, proposed_value, "
            "range_min, range_max, justification, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                proposal.strategy_id,
                proposal.parameter_name,
                proposal.current_value,
                proposal.proposed_value,
                proposal.range_min,
                proposal.range_max,
                proposal.justification,
                proposal.status,
                proposal.created_at.isoformat(),
            ],
        )


def get_reflection_config(
    db: sqlite_utils.Database, domain: str, key: str
) -> str | None:
    """Read a config value from the reflection_config table.

    Args:
        db: Database instance.
        domain: Config domain (e.g. ``"PM-5M"``).
        key: Config key (e.g. ``"min_sessions"``).

    Returns:
        str | None: The config value, or ``None`` if the key does not exist.
    """
    rows = list(
        db.query(
            "SELECT value FROM reflection_config WHERE domain = ? AND key = ?",
            [domain, key],
        )
    )
    return rows[0]["value"] if rows else None


def set_reflection_config(
    db: sqlite_utils.Database, domain: str, key: str, value: str
) -> None:
    """Write or update a config value in the reflection_config table.

    Uses INSERT OR REPLACE to handle the composite PK (domain, key).

    Args:
        db: Database instance.
        domain: Config domain (e.g. ``"PM-5M"``).
        key: Config key (e.g. ``"min_sessions"``).
        value: String value to store.
    """
    db.execute(
        "INSERT OR REPLACE INTO reflection_config (domain, key, value) "
        "VALUES (?, ?, ?)",
        [domain, key, value],
    )
