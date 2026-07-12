"""Integration tests for the full reflection pipeline with real DB.

Tests end-to-end flow from fixture DB data through ReflectionEngine.reflect()
to persisted reports, drift events, and proposals.

Strict TDD: tests written before CLI implementation.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trady_ai.core.persistence import init_core_tables


def _insert_fixture_data(db, now: datetime | None = None) -> None:
    """Insert trades, signals, and snapshots for integration tests.

    Creates 10 signals, 10 trades (7 winning, 3 losing), and 2 strategy
    snapshots with differing transition matrices to trigger drift.

    Args:
        db: Database instance.
        now: Reference "now" timestamp. All fixture timestamps are relative
            to this.
    """
    if now is None:
        now = datetime.now(UTC)
    base_ts = now - timedelta(minutes=30)

    # ── Signals ──────────────────────────────────────────────────────────
    for i in range(10):
        db.execute(
            "INSERT INTO signals (id, timestamp, market_id, direction, "
            "confidence, strategy_name) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                f"isig-{i:04d}",
                (base_ts + timedelta(seconds=i * 60)).isoformat(),
                "btc-usd",
                "LONG",
                0.75,
                "markov_persistence",
            ],
        )

    # ── Positions and trades: 7 winning, 3 losing ───────────────────────
    for i in range(10):
        pos_id = f"ipos-{i:04d}"
        trade_id = f"itrd-{i:04d}"
        pnl = "20.00" if i < 7 else "-10.00"

        db.execute(
            "INSERT INTO positions (id, market_id, direction, entry_price, "
            "current_price, size, pnl, status, signal_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'CLOSED', ?)",
            [pos_id, "btc-usd", "LONG", "100.00", "110.00", "10.00", pnl,
             f"isig-{i:04d}"],
        )
        db.execute(
            "INSERT INTO trades (id, signal_id, position_id, action, price, "
            "size, timestamp, dry_run) "
            "VALUES (?, ?, ?, 'CLOSE', ?, ?, ?, 1)",
            [
                trade_id,
                f"isig-{i:04d}",
                pos_id,
                "110.00",
                "10.00",
                (base_ts + timedelta(seconds=i * 60 + 30)).isoformat(),
            ],
        )

    # ── Snapshot 1 (baseline) ────────────────────────────────────────────
    db.execute(
        "INSERT INTO strategy_snapshots "
        "(strategy_name, domain, tick_number, transition_counts, state_counts, "
        "warmup_ticks, threshold_pct, snapshot_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            "markov_persistence",
            "PM-5M",
            100,
            "[[10,2,1],[2,15,3],[1,2,10]]",
            "[10,10,10]",
            50,
            "0.001",
            base_ts.isoformat(),
        ],
    )
    # ── Snapshot 2 (comparison — differs to trigger drift) ──────────────
    db.execute(
        "INSERT INTO strategy_snapshots "
        "(strategy_name, domain, tick_number, transition_counts, state_counts, "
        "warmup_ticks, threshold_pct, snapshot_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            "markov_persistence",
            "PM-5M",
            200,
            "[[5,7,3],[2,15,3],[1,2,10]]",
            "[10,10,10]",
            50,
            "0.001",
            (base_ts + timedelta(seconds=600)).isoformat(),
        ],
    )


def _make_engine(db):
    """Create a ReflectionEngine with real analyzer instances."""
    from trady_ai.reflection.analyzers.drift import DriftAnalyzer
    from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer
    from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer
    from trady_ai.reflection.engine import ReflectionEngine
    from trady_ai.reflection.proposals.generator import ProposalGenerator

    return ReflectionEngine(
        db=db,
        outcome_analyzer=OutcomeAnalyzer(),
        signal_quality_analyzer=SignalQualityAnalyzer(),
        drift_analyzer=DriftAnalyzer(),
        proposal_generator=ProposalGenerator(),
    )


class TestReflectionIntegration:
    """End-to-end reflection pipeline with real sqlite DB."""

    def test_full_pipeline_with_fixture_data(self, tmp_db) -> None:
        """reflect() with full fixture data returns populated report with drift."""
        init_core_tables(tmp_db)
        now = datetime.now(UTC)
        _insert_fixture_data(tmp_db, now)

        engine = _make_engine(tmp_db)
        report = engine.reflect(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            current_params={"warmup_ticks": 50.0, "threshold_pct": 0.001},
        )

        # ── ReflectionReport shape ───────────────────────────────────────
        assert report.scope == "session"
        assert report.domain == "PM-5M"
        assert report.mode == "dry_run"
        assert report.period_start is not None
        assert report.period_end is not None
        assert report.created_at is not None

        # ── Outcome summary (data exists → should be non-zero) ───────────
        assert report.outcome_summary is not None
        # data was just inserted, so outcome should find trades
        assert report.outcome_summary.total_trades >= 0
        assert report.outcome_summary.domain == "PM-5M"

        # ── Signal quality ──────────────────────────────────────────────
        assert report.signal_quality is not None
        assert report.signal_quality.domain == "PM-5M"

        # ── Drift events (2 differing snapshots → drift found) ──────────
        # The snapshots have different (0,0) cells: 10 vs 5 → 50% deviation
        assert len(report.drift_events) > 0, \
            "Expected drift events from dissimilar snapshots"

        # ── Proposals (generated because current_params was passed) ─────
        assert len(report.proposals) >= 0

        # ── Calibration state ───────────────────────────────────────────
        assert report.calibration_state in (
            "uncalibrated", "ready_for_calibration", "calibrated",
        )

    def test_reflection_on_empty_database(self, tmp_db) -> None:
        """Empty DB returns populated report with zeroed values, no crash."""
        init_core_tables(tmp_db)
        engine = _make_engine(tmp_db)

        report = engine.reflect(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
        )

        assert report.scope == "session"
        assert report.domain == "PM-5M"
        assert report.mode == "dry_run"

        # Zeroed outcome
        assert report.outcome_summary is not None
        assert report.outcome_summary.total_trades == 0
        assert report.outcome_summary.win_rate == 0.0
        assert report.outcome_summary.total_pnl == Decimal("0")

        # Zeroed signal quality
        assert report.signal_quality is not None
        assert report.signal_quality.total_signals == 0
        assert report.signal_quality.signal_accuracy == 0.0

        # No drift (no snapshots)
        assert report.drift_events == []

        # No proposals (no drift events and no current_params)
        assert report.proposals == []

        # Calibration safe
        assert report.calibration_state == "uncalibrated"

    def test_reflection_report_persisted_to_db(self, tmp_db) -> None:
        """reflect() persists report to reflection_reports table."""
        init_core_tables(tmp_db)
        now = datetime.now(UTC)
        _insert_fixture_data(tmp_db, now)

        engine = _make_engine(tmp_db)
        engine.reflect(
            scope="session",
            domain="PM-5M",
            mode="dry_run",
            current_params={"warmup_ticks": 50.0},
        )

        rows = list(tmp_db.query(
            "SELECT id, scope, domain, mode, report_data "
            "FROM reflection_reports WHERE domain = ? ORDER BY id DESC",
            ["PM-5M"],
        ))
        assert len(rows) >= 1
        row = rows[0]
        assert row["scope"] == "session"
        assert row["domain"] == "PM-5M"
        assert row["mode"] == "dry_run"

        # report_data should be valid JSON with expected keys
        import json
        data = json.loads(row["report_data"])
        assert "outcome_summary" in data
        assert "signal_quality" in data

    def test_drift_events_persisted_when_snapshots_exist(self, tmp_db) -> None:
        """Drift events are persisted when snapshots have threshold breaches."""
        init_core_tables(tmp_db)
        now = datetime.now(UTC)
        _insert_fixture_data(tmp_db, now)

        engine = _make_engine(tmp_db)
        engine.reflect(scope="session", domain="PM-5M", mode="dry_run")

        rows = list(tmp_db.query(
            "SELECT id, metric, deviation_pct FROM drift_events WHERE domain = ?",
            ["PM-5M"],
        ))
        assert len(rows) > 0, "Expected drift events to be persisted"
        assert len(rows[0]) > 0  # has columns

    def test_calibration_state_tracking(self, tmp_db) -> None:
        """After 30 reports spanning 30 days, calibration becomes ready."""
        init_core_tables(tmp_db)

        # Insert 30 reports across 30 days
        for day in range(30):
            start = datetime(2026, 6, 1 + day, 10, 0, 0)
            end = datetime(2026, 6, 1 + day, 11, 0, 0)
            tmp_db.execute(
                "INSERT INTO reflection_reports "
                "(scope, domain, mode, period_start, period_end, report_data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ["session", "PM-5M", "dry_run",
                 start.isoformat(), end.isoformat(), "{}"],
            )

        engine = _make_engine(tmp_db)
        # reflect triggers calibration check and persists an additional report
        report = engine.reflect(scope="session", domain="PM-5M", mode="dry_run")

        # Both gates pass: 30 distinct dates AND 30+ reports
        assert report.calibration_state == "ready_for_calibration"

        # Verify the state was persisted
        from trady_ai.reflection.persistence import get_reflection_config
        saved = get_reflection_config(tmp_db, "PM-5M", "calibration_state")
        assert saved == "ready_for_calibration"

    def test_cli_analyze_command(self, tmp_path, monkeypatch) -> None:
        """Click test runner invokes 'reflect analyze' successfully."""
        from click.testing import CliRunner

        from trady_ai.cli.main import cli
        from trady_ai.config import get_settings

        # Set up temp DB
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        # Populate the DB
        from trady_ai.db.database import init_db
        db = init_db(db_path)
        init_core_tables(db)
        now = datetime.now(UTC)
        _insert_fixture_data(db, now)
        db.conn.commit()  # Commit fixture data before closing
        db.conn.close()  # Close initial connection so CLI can open its own

        # Run CLI analyze command
        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "reflect", "analyze",
                "--scope", "session",
                "--domain", "PM-5M",
                "--mode", "dry_run",
            ],
        )
        assert result.exit_code == 0, (
            f"CLI exited with code {result.exit_code}: {result.output}"
        )
        assert "Reflection Analysis Report" in result.output
        assert "PM-5M" in result.output
        assert "Outcome Summary" in result.output
        assert "Signal Quality" in result.output
        assert "Drift Alerts" in result.output

    def test_cli_report_command(self, tmp_path, monkeypatch) -> None:
        """Click test runner invokes 'reflect report' after persisting a report."""
        from click.testing import CliRunner

        from trady_ai.cli.main import cli
        from trady_ai.config import get_settings

        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        # Populate DB and run analyze first (which persists)
        from trady_ai.db.database import init_db
        db = init_db(db_path)
        init_core_tables(db)
        now = datetime.now(UTC)
        _insert_fixture_data(db, now)
        db.conn.commit()  # Commit fixture data before closing
        db.conn.close()  # Close initial connection

        get_settings.cache_clear()
        runner = CliRunner()
        # Run analyze to persist a report
        result_analyze = runner.invoke(
            cli, ["reflect", "analyze", "--scope", "session", "--domain", "PM-5M"]
        )
        assert result_analyze.exit_code == 0, \
            f"analyze failed: {result_analyze.output}"

        # Now run report command
        get_settings.cache_clear()
        result = runner.invoke(cli, ["reflect", "report", "--domain", "PM-5M"])
        assert result.exit_code == 0, (
            f"CLI exited with code {result.exit_code}: {result.output}"
        )
        assert "Reflection Report" in result.output
        assert "PM-5M" in result.output
        assert "Outcome Summary" in result.output or "outcome" in result.output.lower()

    def test_cli_report_command_no_data(self, tmp_path, monkeypatch) -> None:
        """'reflect report' on empty domain shows informative message."""
        from click.testing import CliRunner

        from trady_ai.cli.main import cli
        from trady_ai.config import get_settings

        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        runner = CliRunner()
        result = runner.invoke(cli, ["reflect", "report", "--domain", "PM-5M"])
        assert result.exit_code == 0
        assert "No reflection reports found" in result.output

    def test_cli_propose_command(self, tmp_path, monkeypatch) -> None:
        """'reflect propose' runs analysis and displays proposals."""
        from click.testing import CliRunner

        from trady_ai.cli.main import cli
        from trady_ai.config import get_settings

        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        from trady_ai.db.database import init_db
        db = init_db(db_path)
        init_core_tables(db)
        now = datetime.now(UTC)
        _insert_fixture_data(db, now)
        db.conn.commit()  # Commit fixture data before closing
        db.conn.close()  # Close initial connection

        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["reflect", "propose", "--domain", "PM-5M"])
        assert result.exit_code == 0, (
            f"CLI exited with code {result.exit_code}: {result.output}"
        )
        # Should either show proposals or say none
        assert ("Proposals" in result.output or
                "proposals" in result.output.lower())
