"""Tests for CalibrationAnalyzer — stateless, read-only evidence pipeline.

Tests inject synthetic snapshots and verify EvidenceReport output.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from trady_ai.core.persistence import init_core_tables


def _insert_snapshot(
    db,
    strategy_name: str = "markov_persistence",
    domain: str = "PM-5M",
    tick_number: int = 100,
    transition_counts: list | None = None,
    state_counts: list | None = None,
    state_space_size: int = 3,
    state_generator: str = "directional",
    warmup_ticks: int = 50,
    threshold_pct: str = "0.001",
) -> None:
    """Insert a strategy_snapshot row for testing."""
    if transition_counts is None:
        transition_counts = [[10, 2, 1], [2, 15, 3], [1, 2, 10]]
    if state_counts is None:
        state_counts = [10, 10, 10]

    db.execute(
        "INSERT INTO strategy_snapshots "
        "(strategy_name, domain, tick_number, transition_counts, state_counts, "
        "warmup_ticks, threshold_pct, state_space_size, state_generator, snapshot_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            strategy_name,
            domain,
            tick_number,
            json.dumps(transition_counts),
            json.dumps(state_counts),
            warmup_ticks,
            threshold_pct,
            state_space_size,
            state_generator,
            datetime.now(UTC).isoformat(),
        ],
    )


class TestCalibrationAnalyzer:
    """CalibrationAnalyzer produces deterministic EvidenceReports."""

    def test_no_snapshot_returns_empty_report(self, tmp_db):
        """No snapshots for domain → empty EvidenceReport."""
        init_core_tables(tmp_db)
        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        report = analyzer.analyze(tmp_db, "PM-5M")
        assert report.num_states == 0
        assert report.num_observations == 0
        assert report.aic == 0.0
        assert report.bic == 0.0
        assert report.conditional_entropy == 0.0

    def test_with_snapshot_returns_metrics(self, tmp_db):
        """Single snapshot → computed metrics in report."""
        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db)

        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        report = analyzer.analyze(tmp_db, "PM-5M")

        assert report.num_states == 3
        assert report.num_observations > 0
        assert report.aic > 0
        assert report.bic > 0
        assert isinstance(report.markov_test, dict)
        assert "p_value" in report.markov_test
        assert isinstance(report.state_persistence, dict)
        assert len(report.state_persistence) == 3
        assert isinstance(report.conditional_entropy, float)
        assert isinstance(report.computed_at, str)
        assert report.computed_at != ""

    def test_deterministic_output(self, tmp_db):
        """Same DB state twice → same report values."""
        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db)

        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        r1 = analyzer.analyze(tmp_db, "PM-5M")
        r2 = analyzer.analyze(tmp_db, "PM-5M")

        assert r1.aic == r2.aic
        assert r1.bic == r2.bic
        assert r1.conditional_entropy == r2.conditional_entropy
        assert r1.markov_test["statistic"] == r2.markov_test["statistic"]
        assert r1.state_persistence == r2.state_persistence

    def test_different_domains_independent(self, tmp_db):
        """Different domains produce independent reports."""
        init_core_tables(tmp_db)
        # Insert for PM-5M
        _insert_snapshot(tmp_db, domain="PM-5M",
                         transition_counts=[[10, 2, 1], [2, 15, 3], [1, 2, 10]])
        # Insert for OTHER-DOM
        _insert_snapshot(tmp_db, domain="OTHER-DOM",
                         transition_counts=[[5, 5, 5], [5, 5, 5], [5, 5, 5]])

        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        r1 = analyzer.analyze(tmp_db, "PM-5M")
        r2 = analyzer.analyze(tmp_db, "OTHER-DOM")

        assert r1.aic != r2.aic  # Different matrices → different metrics

    def test_no_db_writes(self, tmp_db):
        """Analyzer never writes to the DB (read-only)."""
        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db)

        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

        # Count tables before
        from trady_ai.reflection.calibration.persistence import init_calibration_tables

        init_calibration_tables(tmp_db)
        initial_count = list(tmp_db.query("SELECT COUNT(*) as c FROM calibration_evidence"))[0]["c"]

        analyzer = CalibrationAnalyzer()
        analyzer.analyze(tmp_db, "PM-5M")

        # Verify no writes to calibration_evidence
        after_count = list(tmp_db.query("SELECT COUNT(*) as c FROM calibration_evidence"))[0]["c"]
        assert after_count == initial_count

    def test_specific_strategy_name(self, tmp_db):
        """Analyze by specific strategy name."""
        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db, strategy_name="custom_strategy")

        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        report = analyzer.analyze(tmp_db, "PM-5M", strategy_name="custom_strategy")
        assert report.num_states == 3
        assert report.num_observations > 0

    def test_different_state_space_sizes(self, tmp_db):
        """Different |S| produce different metrics."""
        init_core_tables(tmp_db)
        # 3-state
        _insert_snapshot(tmp_db, domain="DOM-A", tick_number=1,
                         transition_counts=[[10, 2], [2, 15]],
                         state_counts=[10, 10], state_space_size=2, state_generator="directional")
        # 5-state
        _insert_snapshot(tmp_db, domain="DOM-B", tick_number=1,
                         transition_counts=[[5, 1, 1, 1, 1],
                                            [1, 5, 1, 1, 1],
                                            [1, 1, 5, 1, 1],
                                            [1, 1, 1, 5, 1],
                                            [1, 1, 1, 1, 5]],
                         state_counts=[5, 5, 5, 5, 5], state_space_size=5, state_generator="directional")

        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        r_2 = analyzer.analyze(tmp_db, "DOM-A")
        r_5 = analyzer.analyze(tmp_db, "DOM-B")

        assert r_2.num_states == 2
        assert r_5.num_states == 5
        assert r_2.aic < r_5.aic  # More states → larger AIC

    def test_report_has_all_required_fields(self, tmp_db):
        """EvidenceReport has all fields from spec."""
        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db)

        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        report = analyzer.analyze(tmp_db, "PM-5M")

        assert hasattr(report, "aic")
        assert hasattr(report, "bic")
        assert hasattr(report, "markov_test")
        assert hasattr(report, "state_persistence")
        assert hasattr(report, "conditional_entropy")
        assert hasattr(report, "num_states")
        assert hasattr(report, "num_observations")
        assert hasattr(report, "transition_counts")
        assert hasattr(report, "computed_at")

        # markov_test must have required keys
        for key in ("statistic", "p_value", "df", "reject_null", "significance_level"):
            assert key in report.markov_test


class TestCalibrationAnalyzerWireUp:
    """Verifies CalibrationAnalyzer integrates correctly with ReflectionEngine."""

    def test_engine_accepts_calibration_analyzer(self, tmp_db):
        """ReflectionEngine accepts optional calibration_analyzer."""
        init_core_tables(tmp_db)
        from unittest.mock import MagicMock

        from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer
        from trady_ai.reflection.engine import ReflectionEngine
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        engine = ReflectionEngine(
            db=tmp_db,
            outcome_analyzer=MagicMock(),
            signal_quality_analyzer=MagicMock(),
            drift_analyzer=MagicMock(),
            proposal_generator=MagicMock(spec=ProposalGenerator),
            calibration_analyzer=CalibrationAnalyzer(),
        )
        assert engine._calibration_analyzer is not None

    def test_engine_runs_without_calibration_analyzer(self, tmp_db):
        """ReflectionEngine works without calibration_analyzer (backward compat)."""
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
        assert engine._calibration_analyzer is None
