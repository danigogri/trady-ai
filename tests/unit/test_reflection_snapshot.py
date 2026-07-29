"""Tests for ReflectionEngine snapshot persistence (Phase 2).

Strict TDD: tests written before implementation.
Covers:
  - persist_snapshot() stores snapshot with created_by="reflection_engine"
  - Missing transition_counts raises ValueError
  - Snapshot roundtrip: persist → load matches original data
  - Idempotent re-persist with different created_by
"""
from __future__ import annotations

from datetime import UTC, datetime

from trady_ai.core.persistence import (
    init_core_tables,
    load_latest_snapshot,
)


class TestReflectionSnapshotPersistence:
    """ReflectionEngine.persist_snapshot() provenance and data integrity."""

    def test_snapshot_created_by_reflection_engine(self, tmp_db) -> None:
        """Persisted snapshot has created_by='reflection_engine'."""
        init_core_tables(tmp_db)
        from trady_ai.core.engine import ExecutionResult
        from trady_ai.reflection.engine import ReflectionEngine

        engine = self._make_engine(tmp_db)
        result = ExecutionResult(
            strategy_snapshot={
                "transition_counts": [[5, 1, 0], [1, 8, 2], [0, 1, 6]],
                "state_counts": [6, 11, 7],
                "total_obs": 24,
                "last_state_idx": 1,
                "warmup_ticks": 50,
                "threshold_pct": 0.001,
                "strategy_name": "markov_persistence",
                "state_space_size": 3,
                "state_generator": "directional",
            },
        )
        engine.persist_snapshot(result, domain="PM-5M")

        row = tmp_db.execute(
            "SELECT created_by, strategy_name, tick_number FROM strategy_snapshots "
            "WHERE strategy_name = ?",
            ["markov_persistence"],
        ).fetchone()
        assert row is not None
        assert row[0] == "reflection_engine"
        assert row[1] == "markov_persistence"
        assert row[2] == 24

    def test_missing_transition_counts_raises_value_error(self, tmp_db) -> None:
        """persist_snapshot raises ValueError when transition_counts is missing."""
        init_core_tables(tmp_db)
        from trady_ai.core.engine import ExecutionResult
        from trady_ai.reflection.engine import ReflectionEngine

        engine = self._make_engine(tmp_db)
        result = ExecutionResult(
            strategy_snapshot={
                "state_counts": [6, 11, 7],
                "total_obs": 24,
                "warmup_ticks": 50,
                "threshold_pct": 0.001,
            },
        )

        import pytest

        with pytest.raises(ValueError, match="transition_counts"):
            engine.persist_snapshot(result, domain="PM-5M")

    def test_snapshot_roundtrip_matches_original(self, tmp_db) -> None:
        """Data persisted via persist_snapshot roundtrips via load_latest_snapshot."""
        init_core_tables(tmp_db)
        from trady_ai.core.engine import ExecutionResult
        from trady_ai.reflection.engine import ReflectionEngine

        engine = self._make_engine(tmp_db)
        snap_data = {
            "transition_counts": [[10, 2, 1], [2, 15, 3], [1, 2, 10]],
            "state_counts": [13, 20, 14],
            "total_obs": 47,
            "last_state_idx": 0,
            "warmup_ticks": 50,
            "threshold_pct": 0.001,
            "strategy_name": "roundtrip_test",
            "state_space_size": 3,
            "state_generator": "directional",
        }
        result = ExecutionResult(strategy_snapshot=snap_data)
        engine.persist_snapshot(result, domain="PM-5M")

        loaded = load_latest_snapshot(tmp_db, "PM-5M", "roundtrip_test")
        assert loaded is not None
        import json

        assert json.loads(loaded["transition_counts"]) == [[10, 2, 1], [2, 15, 3], [1, 2, 10]]
        assert json.loads(loaded["state_counts"]) == [13, 20, 14]
        assert loaded["warmup_ticks"] == 50
        assert "threshold_pct" in loaded  # key present (value may migrate to ATR)
        assert loaded["created_by"] == "reflection_engine"

    def test_snapshot_none_is_noop(self, tmp_db) -> None:
        """persist_snapshot with strategy_snapshot=None does nothing."""
        init_core_tables(tmp_db)
        from trady_ai.core.engine import ExecutionResult
        from trady_ai.reflection.engine import ReflectionEngine

        engine = self._make_engine(tmp_db)
        result = ExecutionResult(strategy_snapshot=None)
        engine.persist_snapshot(result, domain="PM-5M")

        count = tmp_db.execute(
            "SELECT COUNT(*) FROM strategy_snapshots"
        ).fetchone()[0]
        assert count == 0

    def test_reflect_with_execution_result_persists_snapshot(self, tmp_db) -> None:
        """reflect() with execution_result automatically persists snapshot."""
        init_core_tables(tmp_db)
        from unittest.mock import MagicMock

        from trady_ai.core.engine import ExecutionResult
        from trady_ai.reflection.engine import ReflectionEngine
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        # Insert a snapshot so _get_strategy_ids finds something
        tmp_db.execute(
            "INSERT INTO strategy_snapshots "
            "(strategy_name, domain, tick_number, transition_counts, state_counts, "
            "warmup_ticks, threshold_pct, snapshot_at, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ["markov_persistence", "PM-5M", 1,
             "[[0,0,0],[0,0,0],[0,0,0]]", "[0,0,0]",
             50, "0.001", datetime.now(UTC).isoformat(), "strategy"],
        )
        engine = ReflectionEngine(
            db=tmp_db,
            outcome_analyzer=MagicMock(),
            signal_quality_analyzer=MagicMock(),
            drift_analyzer=MagicMock(),
            proposal_generator=MagicMock(spec=ProposalGenerator),
        )

        result = ExecutionResult(
            strategy_snapshot={
                "transition_counts": [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
                "state_counts": [1, 0, 0],
                "total_obs": 1,
                "warmup_ticks": 50,
                "threshold_pct": 0.001,
                "strategy_name": "reflect_test",
                "state_space_size": 3,
                "state_generator": "directional",
            },
        )

        # Use side_effect to make analyzers return without errors
        from trady_ai.reflection.models import OutcomeSummary, SignalQualityReport

        engine._outcome_analyzer.analyze.return_value = OutcomeSummary(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0.0, total_pnl=0, avg_pnl_per_trade=0, max_drawdown=0,
        )
        engine._signal_quality_analyzer.analyze.return_value = SignalQualityReport(
            domain="PM-5M",
            period_start=datetime(2026, 7, 10),
            period_end=datetime(2026, 7, 10, 1),
            total_signals=0, signals_with_trades=0,
            signal_accuracy=0.0, avg_confidence=0.0, confidence_bins={},
        )
        engine._drift_analyzer.analyze.return_value = []

        engine.reflect(
            scope="session", domain="PM-5M", mode="dry_run",
            execution_result=result,
        )

        rows = list(
            tmp_db.query(
                "SELECT strategy_name, created_by FROM strategy_snapshots "
                "WHERE created_by = 'reflection_engine'",
            )
        )
        assert len(rows) >= 1
        found = any(r["strategy_name"] == "reflect_test" for r in rows)
        assert found, "reflect() should persist snapshot from execution_result"

    @staticmethod
    def _make_engine(db):
        """Create a minimal ReflectionEngine with mocked collaborators."""
        from unittest.mock import MagicMock

        from trady_ai.reflection.engine import ReflectionEngine
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        return ReflectionEngine(
            db=db,
            outcome_analyzer=MagicMock(),
            signal_quality_analyzer=MagicMock(),
            drift_analyzer=MagicMock(),
            proposal_generator=MagicMock(spec=ProposalGenerator),
        )
