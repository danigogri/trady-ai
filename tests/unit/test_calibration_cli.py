"""Tests for calibration CLI commands.

Calibrate group: review, adopt.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from trady_ai.cli.main import cli
from trady_ai.config import get_settings


def _insert_snapshot(db, domain="PM-5M", transition_counts=None):
    """Insert a minimal strategy_snapshot."""
    from trady_ai.core.persistence import init_core_tables

    init_core_tables(db)

    if transition_counts is None:
        transition_counts = [[10, 2, 1], [2, 15, 3], [1, 2, 10]]

    db.execute(
        "INSERT INTO strategy_snapshots "
        "(strategy_name, domain, tick_number, transition_counts, state_counts, "
        "warmup_ticks, threshold_pct, state_space_size, state_generator, snapshot_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            "markov_persistence",
            domain,
            100,
            json.dumps(transition_counts),
            json.dumps([10, 10, 10]),
            50,
            "0.001",
            3,
            "directional",
            datetime.now(UTC).isoformat(),
        ],
    )


def _init_db(tmp_path, monkeypatch):
    """Initialize a test DB and return it, setting TRADY_AI_DB_PATH env."""
    get_settings.cache_clear()
    from trady_ai.db.database import init_db

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
    db = init_db(db_path)
    from trady_ai.reflection.calibration.persistence import init_calibration_tables

    init_calibration_tables(db)
    return db


def _invoke(args):
    """Invoke CLI with cache cleared."""
    get_settings.cache_clear()
    runner = CliRunner()
    return runner.invoke(cli, args)


class TestCalibrateReview:
    """calibrate review --domain <name> [--strategy <name>]"""

    def test_review_no_data_returns_report(self, tmp_path, monkeypatch):
        """No snapshots → still exits 0 with empty report."""
        _init_db(tmp_path, monkeypatch)
        result = _invoke(["calibrate", "review", "--domain", "PM-5M"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "no data available" in result.output

    def test_review_with_data_shows_metrics(self, tmp_path, monkeypatch):
        """Snapshots exist → metrics displayed."""
        db = _init_db(tmp_path, monkeypatch)
        _insert_snapshot(db)
        result = _invoke(["calibrate", "review", "--domain", "PM-5M"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "AIC" in result.output
        assert "BIC" in result.output
        assert "Entropy" in result.output

    def test_review_with_strategy_name(self, tmp_path, monkeypatch):
        """--strategy filters by strategy name."""
        db = _init_db(tmp_path, monkeypatch)
        _insert_snapshot(db)
        result = _invoke([
            "calibrate", "review", "--domain", "PM-5M",
            "--strategy", "markov_persistence",
        ])
        assert result.exit_code == 0

    def test_review_exit_0(self, tmp_path, monkeypatch):
        """Exit code 0 on success."""
        db = _init_db(tmp_path, monkeypatch)
        _insert_snapshot(db)
        result = _invoke(["calibrate", "review", "--domain", "PM-5M"])
        assert result.exit_code == 0


class TestCalibrateAdopt:
    """calibrate adopt --domain <name> --states <N> --generator <name> [--confirm]"""

    def test_adopt_without_confirm_exits_1(self, tmp_path, monkeypatch):
        """Without --confirm → summary displayed, exit 1, no write."""
        db = _init_db(tmp_path, monkeypatch)
        _insert_snapshot(db)
        result = _invoke([
            "calibrate", "adopt",
            "--domain", "PM-5M",
            "--states", "4",
            "--generator", "directional",
        ])
        assert result.exit_code == 1, f"Exit {result.exit_code}: {result.output}"
        assert "confirm" in result.output.lower() or "--confirm" in result.output

    def test_adopt_with_confirm_exits_0(self, tmp_path, monkeypatch):
        """With --confirm → adoption written, exit 0."""
        db = _init_db(tmp_path, monkeypatch)
        _insert_snapshot(db)
        result = _invoke([
            "calibrate", "adopt",
            "--domain", "PM-5M",
            "--states", "4",
            "--generator", "directional",
            "--confirm",
        ])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "adopted" in result.output.lower() or "Adoption" in result.output

    def test_adopt_validates_states_ge_2(self, tmp_path, monkeypatch):
        """--states must be >= 2."""
        db = _init_db(tmp_path, monkeypatch)
        _insert_snapshot(db)
        result = _invoke([
            "calibrate", "adopt",
            "--domain", "PM-5M",
            "--states", "1",
            "--generator", "directional",
        ])
        assert result.exit_code == 1
        assert "must be >= 2" in result.output.lower()

    def test_adopt_rejects_unknown_generator(self, tmp_path, monkeypatch):
        """Unknown generator name → error."""
        db = _init_db(tmp_path, monkeypatch)
        _insert_snapshot(db)
        result = _invoke([
            "calibrate", "adopt",
            "--domain", "PM-5M",
            "--states", "3",
            "--generator", "nonexistent",
        ])
        assert result.exit_code == 1
        assert "Unknown" in result.output

    def test_adopt_persists_provenance(self, tmp_path, monkeypatch):
        """Adoption record written with timestamp, operator, etc."""
        db = _init_db(tmp_path, monkeypatch)
        monkeypatch.setenv("USER", "test_operator")
        _insert_snapshot(db)
        result = _invoke([
            "calibrate", "adopt",
            "--domain", "PM-5M",
            "--states", "4",
            "--generator", "directional",
            "--confirm",
        ])
        assert result.exit_code == 0

        # Verify record in DB
        rows = list(db.query("SELECT * FROM calibration_adoptions"))
        assert len(rows) >= 1
        row = rows[-1]
        assert row["domain"] == "PM-5M"
        assert row["states"] == 4
        assert row["generator"] == "directional"
        assert row["adopted_at"] != ""
        assert row["reason"] == ""  # empty by default

    def test_adopt_multiple_records_append_only(self, tmp_path, monkeypatch):
        """Multiple adoptions for same domain → both preserved."""
        db = _init_db(tmp_path, monkeypatch)
        _insert_snapshot(db)
        get_settings.cache_clear()

        # First adoption
        _invoke([
            "calibrate", "adopt",
            "--domain", "PM-5M", "--states", "3",
            "--generator", "directional", "--confirm",
        ])
        # Second adoption
        _invoke([
            "calibrate", "adopt",
            "--domain", "PM-5M", "--states", "5",
            "--generator", "volatility", "--confirm",
        ])

        rows = list(db.query("SELECT * FROM calibration_adoptions ORDER BY id"))
        assert len(rows) == 2
        assert rows[0]["states"] == 3
        assert rows[1]["states"] == 5
