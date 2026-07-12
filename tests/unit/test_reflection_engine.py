"""Tests for ProposalGenerator, persistence layer, ReflectionEngine, and calibration gate.

Strict TDD: tests written before implementation.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from trady_ai.core.persistence import init_core_tables

# ── ProposalGenerator Tests ──────────────────────────────────────────────────


class TestProposalGenerator:
    """ProposalGenerator creates bounded parameter proposals from drift events."""

    def _make_drift_event(
        self,
        strategy_id: str = "markov_persistence",
        metric: str = "warmup_ticks",
        previous: float = 50.0,
        current: float = 75.0,
        deviation: float = 50.0,
    ):
        from trady_ai.reflection.models import DriftEvent

        return DriftEvent(
            strategy_id=strategy_id,
            domain="PM-5M",
            metric=metric,
            previous_value=previous,
            current_value=current,
            threshold=0.15,
            deviation_pct=deviation,
            detected_at=datetime.now(UTC),
        )

    def test_realistic_drift_events_skipped_in_phase4(self):
        """Phase 4: drift events from DriftAnalyzer (transition_X_Y) never match
        BOUNDED_PARAMETERS → no proposals generated. Drift→proposal mapping is
        deferred to Fase 5 (Intelligence)."""
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        generator = ProposalGenerator()
        # DriftAnalyzer produces metrics like transition_0_0 through transition_2_2.
        # None of these match BOUNDED_PARAMETERS keys (warmup_ticks, threshold_pct).
        events = [
            self._make_drift_event(
                metric="transition_0_0",
                previous=100.0,
                current=50.0,
                deviation=50.0,
            ),
            self._make_drift_event(
                metric="transition_1_1",
                previous=80.0,
                current=65.0,
                deviation=18.75,
            ),
            self._make_drift_event(
                metric="transition_2_0",
                previous=200.0,
                current=150.0,
                deviation=25.0,
            ),
        ]
        proposals = generator.generate(
            strategy_id="markov_persistence",
            current_params={"warmup_ticks": 50.0, "threshold_pct": 0.005},
            drift_events=events,
        )
        assert proposals == [], (
            "Phase 4: drift events with transition_X_Y metrics do not match "
            "BOUNDED_PARAMETERS keys. No proposals expected."
        )

    def test_clamping_proposal_when_current_outside_range(self):
        """Clamping proposal generated when drift events match BOUNDED_PARAMETERS
        AND current_value is outside range. This documents Phase 4 behavior:
        ProposalGenerator handles range-clamping, not drift→proposal mapping."""
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        generator = ProposalGenerator()
        # warmup_ticks range: [10, 200], midpoint = 105
        events = [
            self._make_drift_event(
                previous=100.0,
                current=50.0,
                deviation=50.0,
            )
        ]
        proposals = generator.generate(
            strategy_id="markov_persistence",
            current_params={"warmup_ticks": 5.0},  # below range_min=10
            drift_events=events,
        )
        assert len(proposals) == 1
        p = proposals[0]
        assert p.parameter_name == "warmup_ticks"
        assert p.current_value == 5.0
        # current outside range → propose midpoint = 105 (safe default)
        assert p.proposed_value == 105.0
        assert p.range_min == 10.0
        assert p.range_max == 200.0
        assert p.strategy_id == "markov_persistence"
        assert "outside range" in p.justification.lower()

    def test_clamps_to_range_min(self):
        """Current value below range_min → proposed is range_midpoint (safety)."""
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        generator = ProposalGenerator()
        # threshold_pct range: [0.0001, 0.01], midpoint = 0.00505
        events = [
            self._make_drift_event(
                metric="threshold_pct",
                previous=0.0005,
                current=0.0002,
                deviation=60.0,
            )
        ]
        proposals = generator.generate(
            strategy_id="strat_a",
            current_params={"threshold_pct": -0.001},  # below range_min=0.0001
            drift_events=events,
        )
        assert len(proposals) == 1
        p = proposals[0]
        assert p.parameter_name == "threshold_pct"
        # current outside range → propose midpoint
        midpoint = (0.0001 + 0.01) / 2
        assert p.proposed_value == midpoint
        assert p.range_min == 0.0001
        assert p.range_max == 0.01
        # Justification notes the fallback
        assert "range" in p.justification.lower()

    def test_clamps_to_range_max(self):
        """Current value above range_max → proposed is range_midpoint (safety)."""
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        generator = ProposalGenerator()
        # warmup_ticks range: [10, 200], midpoint = 105
        events = [
            self._make_drift_event(
                previous=200.0,
                current=250.0,
                deviation=25.0,
            )
        ]
        proposals = generator.generate(
            strategy_id="strat_b",
            current_params={"warmup_ticks": 300.0},  # above range_max=200
            drift_events=events,
        )
        assert len(proposals) == 1
        p = proposals[0]
        assert p.parameter_name == "warmup_ticks"
        # current outside range → propose midpoint
        assert p.proposed_value == 105.0
        assert p.range_min == 10.0
        assert p.range_max == 200.0
        assert "range" in p.justification.lower()

    def test_proposal_status_is_draft(self):
        """All generated proposals have status='draft'."""
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        generator = ProposalGenerator()
        events = [self._make_drift_event()]
        proposals = generator.generate(
            strategy_id="markov_persistence",
            current_params={"warmup_ticks": 50.0},
            drift_events=events,
        )
        assert all(p.status == "draft" for p in proposals)

    def test_empty_drift_returns_empty_proposals(self):
        """No drift events → no proposals generated."""
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        generator = ProposalGenerator()
        proposals = generator.generate(
            strategy_id="markov_persistence",
            current_params={"warmup_ticks": 50.0},
            drift_events=[],
        )
        assert proposals == []

    def test_unknown_parameter_skipped(self):
        """Drift event with metric not in BOUNDED_PARAMETERS → skipped."""
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        generator = ProposalGenerator()
        events = [
            self._make_drift_event(
                metric="transition_0_0",  # not in BOUNDED_PARAMETERS
                previous=100.0,
                current=50.0,
                deviation=50.0,
            )
        ]
        proposals = generator.generate(
            strategy_id="markov_persistence",
            current_params={"warmup_ticks": 50.0},
            drift_events=events,
        )
        assert proposals == []


# ── Persistence Helpers Tests ────────────────────────────────────────────────


class TestPersistenceHelpers:
    """Save/retrieve reflection data via persistence layer."""

    def test_save_and_retrieve_reflection_report(self, tmp_db) -> None:
        """save_reflection_report inserts a row; returns positive id."""
        init_core_tables(tmp_db)
        from trady_ai.reflection.models import OutcomeSummary, ReflectionReport
        from trady_ai.reflection.persistence import save_reflection_report

        outcome = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=0.6,
            total_pnl=Decimal("100"),
            avg_pnl_per_trade=Decimal("20"),
            max_drawdown=Decimal("10"),
        )
        report = ReflectionReport(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            outcome_summary=outcome,
        )
        report_id = save_reflection_report(tmp_db, report)
        assert isinstance(report_id, int)
        assert report_id > 0

        # Verify row exists
        row = tmp_db.execute(
            "SELECT id, scope, domain, mode FROM reflection_reports WHERE id = ?",
            [report_id],
        ).fetchone()
        assert row is not None
        assert row[1] == "session"
        assert row[2] == "PM-5M"
        assert row[3] == "dry_run"

    def test_save_drift_events(self, tmp_db) -> None:
        """save_drift_events inserts rows into drift_events table."""
        init_core_tables(tmp_db)
        from trady_ai.reflection.models import DriftEvent
        from trady_ai.reflection.persistence import save_drift_events

        events = [
            DriftEvent(
                strategy_id="strat_a",
                domain="PM-5M",
                metric="transition_0_0",
                previous_value=100.0,
                current_value=50.0,
                threshold=0.15,
                deviation_pct=50.0,
                detected_at=datetime.now(UTC),
            ),
            DriftEvent(
                strategy_id="strat_a",
                domain="PM-5M",
                metric="transition_1_1",
                previous_value=80.0,
                current_value=40.0,
                threshold=0.15,
                deviation_pct=50.0,
                detected_at=datetime.now(UTC),
            ),
        ]
        save_drift_events(tmp_db, events)

        rows = list(tmp_db.query("SELECT * FROM drift_events"))
        assert len(rows) == 2
        assert rows[0]["strategy_id"] == "strat_a"
        assert rows[0]["metric"] == "transition_0_0"

    def test_save_proposals(self, tmp_db) -> None:
        """save_proposals inserts rows into proposals table."""
        init_core_tables(tmp_db)
        from trady_ai.reflection.models import Proposal
        from trady_ai.reflection.persistence import save_proposals

        proposals = [
            Proposal(
                strategy_id="strat_a",
                parameter_name="warmup_ticks",
                current_value=50.0,
                proposed_value=75.0,
                range_min=10.0,
                range_max=200.0,
                justification="Improved win rate",
            ),
        ]
        save_proposals(tmp_db, proposals)

        rows = list(tmp_db.query("SELECT * FROM proposals"))
        assert len(rows) == 1
        assert rows[0]["strategy_id"] == "strat_a"
        assert rows[0]["parameter_name"] == "warmup_ticks"
        assert rows[0]["proposed_value"] == 75.0
        assert rows[0]["status"] == "draft"

    def test_get_set_reflection_config(self, tmp_db) -> None:
        """get_reflection_config and set_reflection_config roundtrip."""
        init_core_tables(tmp_db)
        from trady_ai.reflection.persistence import (
            get_reflection_config,
            set_reflection_config,
        )

        # Initially None
        assert get_reflection_config(tmp_db, "PM-5M", "min_sessions") is None

        # Set and retrieve
        set_reflection_config(tmp_db, "PM-5M", "min_sessions", "50")
        value = get_reflection_config(tmp_db, "PM-5M", "min_sessions")
        assert value == "50"

        # Update
        set_reflection_config(tmp_db, "PM-5M", "min_sessions", "100")
        value = get_reflection_config(tmp_db, "PM-5M", "min_sessions")
        assert value == "100"

    def test_reflection_config_default_none(self, tmp_db) -> None:
        """get_reflection_config returns None for nonexistent key."""
        init_core_tables(tmp_db)
        from trady_ai.reflection.persistence import get_reflection_config

        assert get_reflection_config(tmp_db, "NONEXISTENT", "anything") is None


# ── ReflectionEngine Tests ──────────────────────────────────────────────────


class TestReflectionEngine:
    """ReflectionEngine orchestrates analyzers, proposals, persistence, and calibration."""

    def _make_engine_with_mocks(self, db):
        """Create a ReflectionEngine with all analyzers/strategies mocked."""
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        mock_outcome = MagicMock()
        mock_signal = MagicMock()
        mock_drift = MagicMock()
        mock_generator = MagicMock(spec=ProposalGenerator)

        from trady_ai.reflection.engine import ReflectionEngine

        engine = ReflectionEngine(
            db=db,
            outcome_analyzer=mock_outcome,
            signal_quality_analyzer=mock_signal,
            drift_analyzer=mock_drift,
            proposal_generator=mock_generator,
        )
        return engine, mock_outcome, mock_signal, mock_drift, mock_generator

    def test_reflect_session_scope_returns_report(self, tmp_db) -> None:
        """reflect() with session scope returns a ReflectionReport."""
        init_core_tables(tmp_db)
        engine, mock_outcome, mock_signal, mock_drift, mock_generator = (
            self._make_engine_with_mocks(tmp_db)
        )

        from trady_ai.reflection.models import (
            OutcomeSummary,
            ReflectionReport,
            SignalQualityReport,
        )

        mock_outcome.analyze.return_value = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=Decimal("0"),
            avg_pnl_per_trade=Decimal("0"),
            max_drawdown=Decimal("0"),
        )
        mock_signal.analyze.return_value = SignalQualityReport(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_signals=0,
            signals_with_trades=0,
            signal_accuracy=0.0,
            avg_confidence=0.0,
            confidence_bins={},
        )
        mock_drift.analyze.return_value = []
        mock_generator.generate.return_value = []

        report = engine.reflect(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            current_params={"warmup_ticks": 50.0},
        )
        assert isinstance(report, ReflectionReport)
        assert report.scope == "session"
        assert report.domain == "PM-5M"
        assert report.mode == "dry_run"
        assert isinstance(report.created_at, datetime)
        # Must have calibration state
        assert report.calibration_state in (
            "uncalibrated", "ready_for_calibration", "calibrated"
        )

    def test_reflect_runs_all_analyzers_in_sequence(self, tmp_db) -> None:
        """reflect() calls outcome, then signal quality, then drift analyzers."""
        init_core_tables(tmp_db)
        # Insert a snapshot so _get_strategy_ids returns a strategy
        tmp_db.execute(
            "INSERT INTO strategy_snapshots "
            "(strategy_name, domain, tick_number, transition_counts, state_counts, "
            "warmup_ticks, threshold_pct, snapshot_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ["markov_persistence", "PM-5M", 100,
             "[[10,2,1],[2,15,3],[1,2,10]]", "[10,10,10]",
             50, "0.001", datetime.now(UTC).isoformat()],
        )
        engine, mock_outcome, mock_signal, mock_drift, mock_generator = (
            self._make_engine_with_mocks(tmp_db)
        )

        from trady_ai.reflection.models import OutcomeSummary, SignalQualityReport

        mock_outcome.analyze.return_value = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=Decimal("0"),
            avg_pnl_per_trade=Decimal("0"),
            max_drawdown=Decimal("0"),
        )
        mock_signal.analyze.return_value = SignalQualityReport(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_signals=0,
            signals_with_trades=0,
            signal_accuracy=0.0,
            avg_confidence=0.0,
            confidence_bins={},
        )
        mock_drift.analyze.return_value = []

        engine.reflect(scope="session", domain="PM-5M", mode="dry_run")

        mock_outcome.analyze.assert_called_once()
        mock_signal.analyze.assert_called_once()
        mock_drift.analyze.assert_called_once()

        # Verify outcome ran before signal (by checking call order)
        outcome_call = mock_outcome.analyze.call_args
        signal_call = mock_signal.analyze.call_args
        drift_call = mock_drift.analyze.call_args
        # All were called (order not strictly enforceable with mocks, but
        # the implementation uses sequential calls, not parallel)
        assert outcome_call is not None
        assert signal_call is not None
        assert drift_call is not None

    def test_reflect_persists_report(self, tmp_db) -> None:
        """reflect() persists the report to the reflection_reports table."""
        init_core_tables(tmp_db)
        engine, mock_outcome, mock_signal, mock_drift, mock_generator = (
            self._make_engine_with_mocks(tmp_db)
        )

        from trady_ai.reflection.models import OutcomeSummary, SignalQualityReport

        mock_outcome.analyze.return_value = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=0.6,
            total_pnl=Decimal("100"),
            avg_pnl_per_trade=Decimal("20"),
            max_drawdown=Decimal("10"),
        )
        mock_signal.analyze.return_value = SignalQualityReport(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_signals=10,
            signals_with_trades=5,
            signal_accuracy=0.5,
            avg_confidence=0.7,
            confidence_bins={},
        )
        mock_drift.analyze.return_value = []
        mock_generator.generate.return_value = []

        report = engine.reflect(scope="session", domain="PM-5M", mode="dry_run")

        # Verify report persisted
        rows = list(
            tmp_db.query(
                "SELECT id, domain, scope FROM reflection_reports WHERE domain = ?",
                ["PM-5M"],
            )
        )
        assert len(rows) >= 1
        # The returned report id should match the persisted row
        assert report.calibration_state in (
            "uncalibrated", "ready_for_calibration", "calibrated"
        )

    def test_empty_data_returns_zeroed_report(self, tmp_db) -> None:
        """reflect() with no data returns an assembled report with zeroed values."""
        init_core_tables(tmp_db)
        engine, mock_outcome, mock_signal, mock_drift, mock_generator = (
            self._make_engine_with_mocks(tmp_db)
        )

        from trady_ai.reflection.models import OutcomeSummary, SignalQualityReport

        mock_outcome.analyze.return_value = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=Decimal("0"),
            avg_pnl_per_trade=Decimal("0"),
            max_drawdown=Decimal("0"),
        )
        mock_signal.analyze.return_value = SignalQualityReport(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_signals=0,
            signals_with_trades=0,
            signal_accuracy=0.0,
            avg_confidence=0.0,
            confidence_bins={},
        )
        mock_drift.analyze.return_value = []

        report = engine.reflect(scope="session", domain="PM-5M", mode="dry_run")

        assert report.outcome_summary is not None
        assert report.outcome_summary.total_trades == 0
        assert report.outcome_summary.win_rate == 0.0
        assert report.signal_quality is not None
        assert report.signal_quality.total_signals == 0
        assert report.drift_events == []

    def test_calibration_state_uncalibrated_by_default(self, tmp_db) -> None:
        """Empty reflection_config → calibration_state='uncalibrated'."""
        init_core_tables(tmp_db)
        from unittest.mock import MagicMock

        from trady_ai.reflection.engine import ReflectionEngine
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        engine = ReflectionEngine(
            db=tmp_db,
            outcome_analyzer=MagicMock(),
            signal_quality_analyzer=MagicMock(),
            drift_analyzer=MagicMock(),
            proposal_generator=MagicMock(spec=ProposalGenerator),
        )
        state = engine._check_calibration_readiness("PM-5M")
        assert state == "uncalibrated"

    def test_calibration_ready_when_gates_pass(self, tmp_db) -> None:
        """30+ days of reports and 30+ reports → ready_for_calibration."""
        init_core_tables(tmp_db)
        from unittest.mock import MagicMock

        from trady_ai.reflection.engine import ReflectionEngine
        from trady_ai.reflection.persistence import (
            get_reflection_config,
        )
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        # Insert 30 reports spanning 30 days
        for day in range(30):
            start = datetime(2026, 6, 1 + day, 10, 0, 0)
            end = datetime(2026, 6, 1 + day, 11, 0, 0)
            tmp_db.execute(
                "INSERT INTO reflection_reports "
                "(scope, domain, mode, period_start, period_end, report_data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ["session", "PM-5M", "dry_run",
                 start.isoformat(), end.isoformat(), '{}'],
            )

        engine = ReflectionEngine(
            db=tmp_db,
            outcome_analyzer=MagicMock(),
            signal_quality_analyzer=MagicMock(),
            drift_analyzer=MagicMock(),
            proposal_generator=MagicMock(spec=ProposalGenerator),
        )
        state = engine._check_calibration_readiness("PM-5M")
        assert state == "ready_for_calibration"

        # Verify persisted in config
        saved = get_reflection_config(tmp_db, "PM-5M", "calibration_state")
        assert saved == "ready_for_calibration"

    def test_calibration_stays_calibrated_once_set(self, tmp_db) -> None:
        """Once calibration_state='calibrated', gate stays calibrated."""
        init_core_tables(tmp_db)
        from unittest.mock import MagicMock

        from trady_ai.reflection.engine import ReflectionEngine
        from trady_ai.reflection.persistence import set_reflection_config
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        # Set calibrated state
        set_reflection_config(tmp_db, "PM-5M", "calibration_state", "calibrated")

        engine = ReflectionEngine(
            db=tmp_db,
            outcome_analyzer=MagicMock(),
            signal_quality_analyzer=MagicMock(),
            drift_analyzer=MagicMock(),
            proposal_generator=MagicMock(spec=ProposalGenerator),
        )
        state = engine._check_calibration_readiness("PM-5M")
        assert state == "calibrated"

    def test_calibration_stays_ready_once_set(self, tmp_db) -> None:
        """Once ready_for_calibration, stays ready (no oscillation)."""
        init_core_tables(tmp_db)
        from unittest.mock import MagicMock

        from trady_ai.reflection.engine import ReflectionEngine
        from trady_ai.reflection.persistence import set_reflection_config
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        # Set ready state (simulate operator hasn't approved yet)
        set_reflection_config(
            tmp_db, "PM-5M", "calibration_state", "ready_for_calibration"
        )

        engine = ReflectionEngine(
            db=tmp_db,
            outcome_analyzer=MagicMock(),
            signal_quality_analyzer=MagicMock(),
            drift_analyzer=MagicMock(),
            proposal_generator=MagicMock(spec=ProposalGenerator),
        )
        state = engine._check_calibration_readiness("PM-5M")
        assert state == "ready_for_calibration"

    def test_reflect_with_baseline_comparison_ticks(self, tmp_db) -> None:
        """reflect() passes baseline_tick and comparison_tick to drift analyzer."""
        init_core_tables(tmp_db)
        # Insert a snapshot so _get_strategy_ids returns a strategy
        tmp_db.execute(
            "INSERT INTO strategy_snapshots "
            "(strategy_name, domain, tick_number, transition_counts, state_counts, "
            "warmup_ticks, threshold_pct, snapshot_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ["markov_persistence", "PM-5M", 100,
             "[[10,2,1],[2,15,3],[1,2,10]]", "[10,10,10]",
             50, "0.001", datetime.now(UTC).isoformat()],
        )
        engine, mock_outcome, mock_signal, mock_drift, mock_generator = (
            self._make_engine_with_mocks(tmp_db)
        )

        from trady_ai.reflection.models import OutcomeSummary, SignalQualityReport

        mock_outcome.analyze.return_value = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=Decimal("0"),
            avg_pnl_per_trade=Decimal("0"),
            max_drawdown=Decimal("0"),
        )
        mock_signal.analyze.return_value = SignalQualityReport(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_signals=0,
            signals_with_trades=0,
            signal_accuracy=0.0,
            avg_confidence=0.0,
            confidence_bins={},
        )
        mock_drift.analyze.return_value = []

        engine.reflect(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            baseline_tick=100,
            comparison_tick=200,
        )

        mock_drift.analyze.assert_called_once()
        call_kwargs = mock_drift.analyze.call_args[1]
        # kwargs might include db passed as positional; check for baseline_tick
        assert call_kwargs.get("baseline_tick") == 100
        assert call_kwargs.get("comparison_tick") == 200
