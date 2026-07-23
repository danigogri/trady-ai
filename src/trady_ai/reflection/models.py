"""Data models for the Reflection Systems module.

Provides dataclasses for reflection reports, drift events, proposals,
and supporting analysis types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

VALID_PROPOSAL_STATUSES: set[str] = {"draft", "submitted"}


class InvalidProposalStatusError(ValueError):
    """Raised when an invalid status is assigned to a Proposal."""


@dataclass
class OutcomeSummary:
    """Trade outcome analysis for a domain/time range."""

    domain: str
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: Decimal
    avg_pnl_per_trade: Decimal
    max_drawdown: Decimal


@dataclass
class SignalQualityReport:
    """Signal quality analysis."""

    domain: str
    period_start: datetime
    period_end: datetime
    total_signals: int
    signals_with_trades: int
    signal_accuracy: float
    avg_confidence: float
    confidence_bins: dict[str, dict[str, float]]


@dataclass
class DriftEvent:
    """A detected deviation in strategy behavior."""

    strategy_id: str
    domain: str
    metric: str
    previous_value: float
    current_value: float
    threshold: float
    deviation_pct: float
    detected_at: datetime


@dataclass
class Proposal:
    """A bounded parameter adjustment proposal.

    Status lifecycle: draft → submitted. States approved/rejected/deployed
    are managed by Governance (external to Reflection).
    """

    strategy_id: str
    parameter_name: str
    current_value: float
    proposed_value: float
    range_min: float
    range_max: float
    justification: str
    status: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.status not in VALID_PROPOSAL_STATUSES:
            raise InvalidProposalStatusError(
                f"Invalid status: {self.status!r}. Must be one of {VALID_PROPOSAL_STATUSES}"
            )


@dataclass
class ReflectionReport:
    """Complete reflection analysis report."""

    scope: str
    domain: str
    mode: str
    period_start: datetime
    period_end: datetime
    outcome_summary: OutcomeSummary | None = None
    signal_quality: SignalQualityReport | None = None
    drift_events: list[DriftEvent] = field(default_factory=list)
    proposals: list[Proposal] = field(default_factory=list)
    calibration_state: str = "uncalibrated"
    evidence_report: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
