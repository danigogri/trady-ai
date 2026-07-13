"""Tests for paper_trading models.

Strict TDD: tests written before implementation (RED phase).
"""
from __future__ import annotations


class TestSessionState:
    """SessionState StrEnum values — all 9 members must match spec."""

    def test_idle(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.IDLE == "idle"

    def test_pre_flight(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.PRE_FLIGHT == "pre_flight"

    def test_capturing(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.CAPTURING == "capturing"

    def test_executing(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.EXECUTING == "executing"

    def test_reflecting(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.REFLECTING == "reflecting"

    def test_verifying(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.VERIFYING == "verifying"

    def test_bundling(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.BUNDLING == "bundling"

    def test_complete(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.COMPLETE == "complete"

    def test_error(self):
        from trady_ai.paper_trading.models import SessionState

        assert SessionState.ERROR == "error"


class TestContractViolation:
    """ContractViolation dataclass — field-level assertions."""

    def test_all_fields_roundtrip(self):
        from trady_ai.paper_trading.models import ContractViolation

        v = ContractViolation(
            contract_name="DRY_RUN_ENFORCED",
            severity="CRITICAL",
            detail="Execution mode is 'live'",
            timestamp="2024-01-01T00:00:00",
        )
        assert v.contract_name == "DRY_RUN_ENFORCED"
        assert v.severity == "CRITICAL"
        assert v.detail == "Execution mode is 'live'"
        assert v.timestamp == "2024-01-01T00:00:00"

    def test_warning_severity(self):
        from trady_ai.paper_trading.models import ContractViolation

        v = ContractViolation(
            contract_name="DETERMINISTIC_REPRODUCIBILITY",
            severity="WARNING",
            detail="Replay verification deferred",
            timestamp="2024-06-01T12:00:00",
        )
        assert v.severity == "WARNING"


class TestSessionReport:
    """SessionReport dataclass — default values and construction."""

    def test_default_values(self):
        from trady_ai.paper_trading.models import SessionReport

        report = SessionReport(
            day=1,
            domain="PM-5M",
            event_count=10,
            trade_count=5,
            reflection_report_id=42,
        )
        assert report.contract_results == []
        assert report.stage_timestamps == {}
        assert report.calibration_state == "not_ready"

    def test_reflection_report_id_none(self):
        from trady_ai.paper_trading.models import SessionReport

        report = SessionReport(
            day=5,
            domain="PM-5M",
            event_count=0,
            trade_count=0,
            reflection_report_id=None,
        )
        assert report.reflection_report_id is None

    def test_calibration_state_override(self):
        from trady_ai.paper_trading.models import SessionReport

        report = SessionReport(
            day=30,
            domain="PM-5M",
            event_count=100,
            trade_count=50,
            reflection_report_id=1,
            calibration_state="ready_for_calibration",
        )
        assert report.calibration_state == "ready_for_calibration"

    def test_with_contract_violations(self):
        from trady_ai.paper_trading.models import ContractViolation, SessionReport

        violations = [
            ContractViolation(
                contract_name="NO_REAL_FUNDS",
                severity="CRITICAL",
                detail="Test detail",
                timestamp="2024-01-01T00:00:00",
            )
        ]
        report = SessionReport(
            day=1,
            domain="PM-5M",
            event_count=10,
            trade_count=5,
            reflection_report_id=3,
            contract_results=violations,
        )
        assert len(report.contract_results) == 1
        assert report.contract_results[0].contract_name == "NO_REAL_FUNDS"

    def test_stage_timestamps(self):
        from trady_ai.paper_trading.models import SessionReport

        report = SessionReport(
            day=1,
            domain="PM-5M",
            event_count=10,
            trade_count=5,
            reflection_report_id=1,
            stage_timestamps={
                "PRE_FLIGHT": "2024-01-01T00:00:00",
                "COMPLETE": "2024-01-01T01:00:00",
            },
        )
        assert report.stage_timestamps["PRE_FLIGHT"] == "2024-01-01T00:00:00"
        assert report.stage_timestamps["COMPLETE"] == "2024-01-01T01:00:00"


class TestSessionManifest:
    """SessionManifest dataclass — default values and construction."""

    def test_default_artifact_checksums(self):
        from trady_ai.paper_trading.models import SessionManifest

        m = SessionManifest(day=1, domain="PM-5M", created_at="2024-01-01T00:00:00")
        assert m.artifact_checksums == {}

    def test_with_checksums(self):
        from trady_ai.paper_trading.models import SessionManifest

        m = SessionManifest(
            day=1,
            domain="PM-5M",
            created_at="2024-01-01T00:00:00",
            artifact_checksums={"session_report.json": "abc123def456"},
        )
        assert m.artifact_checksums["session_report.json"] == "abc123def456"
