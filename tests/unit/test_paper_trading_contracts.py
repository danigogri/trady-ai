"""Tests for paper_trading operational contracts.

Strict TDD: tests written before implementation (RED phase).
Each contract function tested: pass (empty list), fail (ContractViolation), edge case.
"""
from __future__ import annotations

from datetime import UTC, datetime

import sqlite_utils

from trady_ai.core.persistence import init_core_tables

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_db() -> sqlite_utils.Database:
    """Create a fresh in-memory DB with core tables for contract tests."""
    db = sqlite_utils.Database(memory=True)
    init_core_tables(db)
    return db


def _insert_trade(
    db: sqlite_utils.Database,
    trade_id: str = "t-1",
    dry_run: int = 1,
) -> None:
    """Insert a minimal trade row for contract testing."""
    db["trades"].insert({
        "id": trade_id,
        "signal_id": "sig-1",
        "position_id": "pos-1",
        "action": "OPEN",
        "price": "100.0",
        "size": "1.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "dry_run": dry_run,
    })


def _insert_reflection_report(
    db: sqlite_utils.Database,
    domain: str = "PM-5M",
    created_at: str | None = None,
) -> int:
    """Insert a minimal reflection_report, return its id."""
    now = created_at or datetime.now(UTC).isoformat()
    db.execute(
        """INSERT INTO reflection_reports
           (scope, domain, mode, period_start, period_end, report_data, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ["daily", domain, "dry_run", now, now, "{}", now],
    )
    row = db.execute("SELECT MAX(id) FROM reflection_reports").fetchone()
    return int(row[0]) if row and row[0] else 0


# ── DRY_RUN_ENFORCED ───────────────────────────────────────────────────────────


class TestDryRunEnforced:
    """Contract: execution mode must be 'dry_run'."""

    def test_dry_run_mode_passes(self):
        from trady_ai.paper_trading.contracts import dry_run_enforced

        result = dry_run_enforced("dry_run")
        assert result == []

    def test_live_mode_fails_critical(self):
        from trady_ai.paper_trading.contracts import dry_run_enforced
        from trady_ai.paper_trading.models import ContractViolation

        result = dry_run_enforced("live")
        assert len(result) == 1
        assert isinstance(result[0], ContractViolation)
        assert result[0].severity == "CRITICAL"
        assert result[0].contract_name == "DRY_RUN_ENFORCED"
        assert "live" in result[0].detail

    def test_simulation_mode_fails(self):
        from trady_ai.paper_trading.contracts import dry_run_enforced
        from trady_ai.paper_trading.models import ContractViolation

        result = dry_run_enforced("simulation")
        assert len(result) == 1
        assert isinstance(result[0], ContractViolation)
        assert result[0].severity == "CRITICAL"
        assert "simulation" in result[0].detail


# ── NO_REAL_FUNDS ──────────────────────────────────────────────────────────────


class TestNoRealFunds:
    """Contract: no trades with dry_run=0."""

    def test_no_trades_passes(self):
        from trady_ai.paper_trading.contracts import no_real_funds

        db = _make_db()
        result = no_real_funds(db)
        assert result == []

    def test_all_dry_run_trades_passes(self):
        from trady_ai.paper_trading.contracts import no_real_funds

        db = _make_db()
        _insert_trade(db, "t-1", dry_run=1)
        _insert_trade(db, "t-2", dry_run=1)
        result = no_real_funds(db)
        assert result == []

    def test_real_trade_detected_critical(self):
        from trady_ai.paper_trading.contracts import no_real_funds
        from trady_ai.paper_trading.models import ContractViolation

        db = _make_db()
        _insert_trade(db, "t-1", dry_run=0)
        result = no_real_funds(db)
        assert len(result) == 1
        assert isinstance(result[0], ContractViolation)
        assert result[0].severity == "CRITICAL"
        assert result[0].contract_name == "NO_REAL_FUNDS"
        assert "dry_run=0" in result[0].detail or "real" in result[0].detail.lower()

    def test_mixed_trades_detects_real(self):
        from trady_ai.paper_trading.contracts import no_real_funds

        db = _make_db()
        _insert_trade(db, "t-1", dry_run=1)
        _insert_trade(db, "t-2", dry_run=0)
        _insert_trade(db, "t-3", dry_run=1)
        result = no_real_funds(db)
        assert len(result) == 1

    def test_empty_trades_table_passes(self):
        from trady_ai.paper_trading.contracts import no_real_funds

        db = sqlite_utils.Database(memory=True)
        db.execute(
            "CREATE TABLE IF NOT EXISTS trades (id TEXT, dry_run INTEGER DEFAULT 1)"
        )
        result = no_real_funds(db)
        assert result == []


# ── TEMPORAL_INTEGRITY ─────────────────────────────────────────────────────────


class TestTemporalIntegrity:
    """Contract: no overlapping event range for same domain."""

    def test_no_processed_events_passes(self):
        from trady_ai.paper_trading.contracts import temporal_integrity

        db = _make_db()
        # No execution_log entries → no overlap
        result = temporal_integrity(db, "PM-5M", last_processed_seq=0)
        assert result == []

    def test_overlapping_seq_fails_critical(self):
        from trady_ai.paper_trading.contracts import temporal_integrity
        from trady_ai.paper_trading.models import ContractViolation

        db = _make_db()
        # Simulate already-processed events up to tick 50
        db["execution_log"].insert(
            {
                "tick_number": 50,
                "market_id": "0x123",
                "input_price": "100.0",
                "input_volume": "10.0",
                "state": "NEUTRAL",
                "signal_id": None,
                "decision_action": "HOLD",
                "decision_reason": "test",
                "trade_id": None,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        # Session claims to start at seq 25, but 50 already processed → overlap
        result = temporal_integrity(db, "PM-5M", last_processed_seq=25)
        assert len(result) == 1
        assert isinstance(result[0], ContractViolation)
        assert result[0].severity == "CRITICAL"
        assert result[0].contract_name == "TEMPORAL_INTEGRITY"
        assert "overlapping" in result[0].detail.lower()

    def test_non_overlapping_seq_passes(self):
        from trady_ai.paper_trading.contracts import temporal_integrity

        db = _make_db()
        db["execution_log"].insert(
            {
                "tick_number": 50,
                "market_id": "0x123",
                "input_price": "100.0",
                "input_volume": "10.0",
                "state": "NEUTRAL",
                "signal_id": None,
                "decision_action": "HOLD",
                "decision_reason": "test",
                "trade_id": None,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        # Session starts at seq 100 → beyond what was processed (50) → no overlap
        result = temporal_integrity(db, "PM-5M", last_processed_seq=100)
        assert result == []

    def test_multiple_sessions_same_day_passes(self):
        """Multiple sessions per calendar day are expected — no overlap check by date."""
        from trady_ai.paper_trading.contracts import temporal_integrity

        db = _make_db()
        # Simulate first session processed up to tick 100
        db["execution_log"].insert(
            {
                "tick_number": 100,
                "market_id": "0x123",
                "input_price": "100.0",
                "input_volume": "10.0",
                "state": "NEUTRAL",
                "signal_id": None,
                "decision_action": "HOLD",
                "decision_reason": "test",
                "trade_id": None,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        # Second session same day → starts at seq 101 (beyond what was processed)
        result = temporal_integrity(db, "PM-5M", last_processed_seq=101)
        assert result == []


# ── EVIDENCE_COMPLETENESS ──────────────────────────────────────────────────────


class TestEvidenceCompleteness:
    """Contract: reflection_report must exist after REFLECTING stage."""

    def test_report_exists_passes(self):
        from trady_ai.paper_trading.contracts import evidence_completeness

        db = _make_db()
        _insert_reflection_report(db, domain="PM-5M")
        result = evidence_completeness(db, "PM-5M", 1)
        assert result == []

    def test_no_report_fails_critical(self):
        from trady_ai.paper_trading.contracts import evidence_completeness
        from trady_ai.paper_trading.models import ContractViolation

        db = _make_db()
        result = evidence_completeness(db, "PM-5M", 1)
        assert len(result) == 1
        assert isinstance(result[0], ContractViolation)
        assert result[0].severity == "CRITICAL"
        assert result[0].contract_name == "EVIDENCE_COMPLETENESS"

    def test_report_for_different_domain_fails(self):
        from trady_ai.paper_trading.contracts import evidence_completeness

        db = _make_db()
        _insert_reflection_report(db, domain="OTHER-DOMAIN")
        result = evidence_completeness(db, "PM-5M", 1)
        assert len(result) == 1


# ── DETERMINISTIC_REPRODUCIBILITY ──────────────────────────────────────────────


class TestDeterministicReproducibility:
    """Contract: placeholder — always returns WARNING (deferred)."""

    def test_always_returns_warning(self):
        from trady_ai.paper_trading.contracts import (
            deterministic_reproducibility,
        )
        from trady_ai.paper_trading.models import ContractViolation

        result = deterministic_reproducibility()
        assert len(result) == 1
        assert isinstance(result[0], ContractViolation)
        assert result[0].severity == "WARNING"
        assert result[0].contract_name == "DETERMINISTIC_REPRODUCIBILITY"


# ── REFLECTION_ISOLATION ────────────────────────────────────────────────────────


class TestReflectionIsolation:
    """Contract: placeholder — always returns empty (enforced via import boundary)."""

    def test_always_returns_empty(self):
        from trady_ai.paper_trading.contracts import reflection_isolation

        result = reflection_isolation()
        assert result == []


# ── VALIDATE_ISOLATION_BOUNDARY ────────────────────────────────────────────────


class TestValidateIsolationBoundary:
    """Contract: session.py must not import forbidden modules."""

    def test_no_session_file_exists_returns_empty(self):
        """When session.py does not exist, no violation (PR #1 scenario)."""
        from trady_ai.paper_trading.contracts import validate_isolation_boundary

        result = validate_isolation_boundary("/tmp/nonexistent/session.py")
        assert result == []

    def test_clean_session_passes(self, tmp_path):
        """Session importing stdlib and allowed modules passes."""
        from trady_ai.paper_trading.contracts import validate_isolation_boundary

        session_file = tmp_path / "session.py"
        session_file.write_text(
            "import datetime\nfrom trady_ai.reflection.engine import ReflectionEngine\n"
        )
        result = validate_isolation_boundary(str(session_file))
        assert result == []

    def test_forbidden_strategies_import_fails_critical(self, tmp_path):
        from trady_ai.paper_trading.contracts import validate_isolation_boundary
        from trady_ai.paper_trading.models import ContractViolation

        session_file = tmp_path / "session.py"
        session_file.write_text("import trady_ai.strategies\n")
        result = validate_isolation_boundary(str(session_file))
        assert len(result) == 1
        assert isinstance(result[0], ContractViolation)
        assert result[0].severity == "CRITICAL"
        assert "strategies" in result[0].detail

    def test_forbidden_intelligence_import_fails(self, tmp_path):
        from trady_ai.paper_trading.contracts import validate_isolation_boundary

        session_file = tmp_path / "session.py"
        session_file.write_text("import trady_ai.intelligence\n")
        result = validate_isolation_boundary(str(session_file))
        assert len(result) == 1

    def test_forbidden_governance_from_import_fails(self, tmp_path):
        from trady_ai.paper_trading.contracts import validate_isolation_boundary

        session_file = tmp_path / "session.py"
        session_file.write_text("from trady_ai.governance import something\n")
        result = validate_isolation_boundary(str(session_file))
        assert len(result) == 1

    def test_multiple_forbidden_imports_all_caught(self, tmp_path):
        from trady_ai.paper_trading.contracts import validate_isolation_boundary

        session_file = tmp_path / "session.py"
        session_file.write_text(
            "import trady_ai.strategies.markov\n"
            "from trady_ai.intelligence import optimizer\n"
        )
        result = validate_isolation_boundary(str(session_file))
        assert len(result) == 2

    def test_allowed_core_import_passes(self, tmp_path):
        from trady_ai.paper_trading.contracts import validate_isolation_boundary

        session_file = tmp_path / "session.py"
        session_file.write_text(
            "from trady_ai.core.persistence import init_core_tables\n"
            "from trady_ai.paper_trading.models import SessionReport\n"
        )
        result = validate_isolation_boundary(str(session_file))
        assert result == []
