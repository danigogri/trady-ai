"""Tests for reflection dataclass models.

Covers: OutcomeSummary, SignalQualityReport, DriftEvent, Proposal, ReflectionReport.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from trady_ai.reflection.models import (
    VALID_PROPOSAL_STATUSES,
    DriftEvent,
    InvalidProposalStatusError,
    OutcomeSummary,
    Proposal,
    ReflectionReport,
    SignalQualityReport,
)


class TestOutcomeSummary:
    def test_construct_with_decimal_fields(self) -> None:
        """OutcomeSummary stores Decimal fields correctly."""
        summary = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 1),
            period_end=datetime(2026, 7, 10),
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=0.6,
            total_pnl=Decimal("1500.00"),
            avg_pnl_per_trade=Decimal("15.00"),
            max_drawdown=Decimal("-200.00"),
        )
        assert summary.domain == "PM-5M"
        assert summary.total_trades == 100
        assert summary.win_rate == 0.6
        assert isinstance(summary.total_pnl, Decimal)
        assert summary.total_pnl == Decimal("1500.00")
        assert isinstance(summary.avg_pnl_per_trade, Decimal)
        assert summary.avg_pnl_per_trade == Decimal("15.00")
        assert isinstance(summary.max_drawdown, Decimal)
        assert summary.max_drawdown == Decimal("-200.00")

    def test_winning_plus_losing_equals_total(self) -> None:
        """Convenience check: winning + losing should match total_trades."""
        summary = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 1),
            period_end=datetime(2026, 7, 10),
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            win_rate=0.6,
            total_pnl=Decimal("500.00"),
            avg_pnl_per_trade=Decimal("10.00"),
            max_drawdown=Decimal("-50.00"),
        )
        assert summary.winning_trades + summary.losing_trades == summary.total_trades


class TestSignalQualityReport:
    def test_construct_with_all_fields(self) -> None:
        """SignalQualityReport stores all fields."""
        report = SignalQualityReport(
            domain="PM-5M",
            period_start=datetime(2026, 7, 1),
            period_end=datetime(2026, 7, 10),
            total_signals=200,
            signals_with_trades=150,
            signal_accuracy=0.75,
            avg_confidence=0.65,
            confidence_bins={},
        )
        assert report.total_signals == 200
        assert report.signal_accuracy == 0.75
        assert report.avg_confidence == 0.65

    def test_signal_accuracy_ratio(self) -> None:
        """Signal accuracy is signals_with_trades / total_signals."""
        report = SignalQualityReport(
            domain="PM-5M",
            period_start=datetime(2026, 7, 1),
            period_end=datetime(2026, 7, 10),
            total_signals=100,
            signals_with_trades=30,
            signal_accuracy=0.3,
            avg_confidence=0.5,
            confidence_bins={},
        )
        assert report.signal_accuracy == 0.3


class TestDriftEvent:
    def test_construct_with_float_precision(self) -> None:
        """DriftEvent stores float values with correct precision."""
        event = DriftEvent(
            strategy_id="markov_persistence",
            domain="PM-5M",
            metric="transition_UP_UP",
            previous_value=0.6,
            current_value=0.42,
            threshold=0.15,
            deviation_pct=30.0,
            detected_at=datetime(2026, 7, 10, 12, 0, 0),
        )
        assert event.strategy_id == "markov_persistence"
        assert event.previous_value == 0.6
        assert event.current_value == 0.42
        assert event.deviation_pct == 30.0
        assert event.metric == "transition_UP_UP"

    def test_drift_event_threshold_comparison(self) -> None:
        """Deviation exceeds threshold -> flagged."""
        event = DriftEvent(
            strategy_id="strat_a",
            domain="PM-5M",
            metric="transition_UP_DOWN",
            previous_value=0.5,
            current_value=0.3,
            threshold=0.15,
            deviation_pct=40.0,
            detected_at=datetime(2026, 7, 10),
        )
        assert event.deviation_pct > event.threshold


class TestProposal:
    def test_construct_with_draft_status(self) -> None:
        """Proposal with status='draft' is valid."""
        proposal = Proposal(
            strategy_id="markov_persistence",
            parameter_name="warmup_ticks",
            current_value=50.0,
            proposed_value=75.0,
            range_min=10.0,
            range_max=200.0,
            justification="Improved win rate observed",
            status="draft",
        )
        assert proposal.strategy_id == "markov_persistence"
        assert proposal.status == "draft"
        assert proposal.parameter_name == "warmup_ticks"
        assert proposal.current_value == 50.0
        assert proposal.proposed_value == 75.0

    def test_construct_with_submitted_status(self) -> None:
        """Proposal with status='submitted' is valid."""
        proposal = Proposal(
            strategy_id="directional_persistence",
            parameter_name="threshold_pct",
            current_value=0.001,
            proposed_value=0.005,
            range_min=0.0001,
            range_max=0.01,
            justification="Reduce noise sensitivity",
            status="submitted",
        )
        assert proposal.status == "submitted"

    def test_rejects_invalid_status(self) -> None:
        """Proposal raises InvalidProposalStatusError for invalid status."""
        with pytest.raises(InvalidProposalStatusError):
            Proposal(
                strategy_id="test",
                parameter_name="warmup_ticks",
                current_value=50.0,
                proposed_value=100.0,
                range_min=10.0,
                range_max=200.0,
                justification="Test",
                status="approved",  # invalid — only draft or submitted
            )

    @pytest.mark.parametrize("valid_status", sorted(VALID_PROPOSAL_STATUSES))
    def test_all_valid_statuses_accepted(self, valid_status: str) -> None:
        """Every value in VALID_PROPOSAL_STATUSES is accepted."""
        proposal = Proposal(
            strategy_id="test",
            parameter_name="warmup_ticks",
            current_value=50.0,
            proposed_value=100.0,
            range_min=10.0,
            range_max=200.0,
            justification="Test",
            status=valid_status,
        )
        assert proposal.status == valid_status

    def test_default_status_is_draft(self) -> None:
        """Default status is 'draft'."""
        proposal = Proposal(
            strategy_id="test",
            parameter_name="warmup_ticks",
            current_value=50.0,
            proposed_value=100.0,
            range_min=10.0,
            range_max=200.0,
            justification="Test",
        )
        assert proposal.status == "draft"

    def test_created_at_set_when_not_provided(self) -> None:
        """created_at defaults to a datetime when not provided."""
        proposal = Proposal(
            strategy_id="test",
            parameter_name="warmup_ticks",
            current_value=50.0,
            proposed_value=100.0,
            range_min=10.0,
            range_max=200.0,
            justification="Test",
        )
        assert isinstance(proposal.created_at, datetime)


class TestReflectionReport:
    def test_construct_with_all_fields(self) -> None:
        """ReflectionReport constructed with all fields."""
        outcome = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 1),
            period_end=datetime(2026, 7, 10),
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=0.6,
            total_pnl=Decimal("1500.00"),
            avg_pnl_per_trade=Decimal("15.00"),
            max_drawdown=Decimal("-200.00"),
        )
        report = ReflectionReport(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            period_start=datetime(2026, 7, 10, 10, 0, 0),
            period_end=datetime(2026, 7, 10, 11, 0, 0),
            outcome_summary=outcome,
            calibration_state="uncalibrated",
        )
        assert report.scope == "session"
        assert report.domain == "PM-5M"
        assert report.mode == "dry_run"
        assert report.outcome_summary is outcome
        assert report.calibration_state == "uncalibrated"
        assert report.drift_events == []
        assert report.proposals == []

    def test_forward_references_drift_events(self) -> None:
        """ReflectionReport accepts list[DriftEvent] (forward ref working)."""
        event = DriftEvent(
            strategy_id="markov_persistence",
            domain="PM-5M",
            metric="transition_UP_UP",
            previous_value=0.6,
            current_value=0.42,
            threshold=0.15,
            deviation_pct=30.0,
            detected_at=datetime(2026, 7, 10),
        )
        report = ReflectionReport(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 11),
            drift_events=[event],
        )
        assert len(report.drift_events) == 1
        assert report.drift_events[0] is event
        assert report.drift_events[0].metric == "transition_UP_UP"

    def test_forward_references_proposals(self) -> None:
        """ReflectionReport accepts list[Proposal] (forward ref working)."""
        proposal = Proposal(
            strategy_id="markov_persistence",
            parameter_name="warmup_ticks",
            current_value=50.0,
            proposed_value=75.0,
            range_min=10.0,
            range_max=200.0,
            justification="Test",
        )
        report = ReflectionReport(
            scope="daily",
            domain="PM-5M",
            mode="dry_run",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 11),
            proposals=[proposal],
        )
        assert len(report.proposals) == 1
        assert report.proposals[0].parameter_name == "warmup_ticks"

    def test_default_calibration_state(self) -> None:
        """Default calibration_state is 'uncalibrated'."""
        report = ReflectionReport(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 11),
        )
        assert report.calibration_state == "uncalibrated"

    def test_created_at_set_when_not_provided(self) -> None:
        """created_at defaults to a datetime when not provided."""
        report = ReflectionReport(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 11),
        )
        assert isinstance(report.created_at, datetime)
