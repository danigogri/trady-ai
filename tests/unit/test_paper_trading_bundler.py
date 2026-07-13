"""Tests for EvidenceBundler.

Strict TDD: tests written before implementation (RED phase).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
import sqlite_utils

from trady_ai.core.persistence import init_core_tables
from trady_ai.paper_trading.models import ContractViolation, SessionReport


def _make_db() -> sqlite_utils.Database:
    """Create a fresh in-memory DB with core tables."""
    db = sqlite_utils.Database(memory=True)
    init_core_tables(db)
    return db


class TestEvidenceBundlerBundle:
    """EvidenceBundler.bundle() — output structure and determinism."""

    def _make_report(self, day: int = 1) -> SessionReport:
        return SessionReport(
            day=day,
            domain="PM-5M",
            event_count=10,
            trade_count=5,
            reflection_report_id=1,
        )

    def test_bundle_creates_manifest_with_checksums(self, tmp_path):
        """manifest.json contains day, domain, created_at, artifact_checksums."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))
        report = self._make_report()

        bundle_path = bundler.bundle(report)

        manifest_file = bundle_path / "manifest.json"
        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text())
        assert manifest["day"] == 1
        assert manifest["domain"] == "PM-5M"
        assert "created_at" in manifest
        assert "artifact_checksums" in manifest
        assert "session_report.json" in manifest["artifact_checksums"]
        assert "contracts.json" in manifest["artifact_checksums"]

    def test_bundle_creates_session_report_json(self, tmp_path):
        """session_report.json contains the full SessionReport data."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))
        report = self._make_report()

        bundle_path = bundler.bundle(report)

        report_file = bundle_path / "session_report.json"
        assert report_file.exists()
        data = json.loads(report_file.read_text())
        assert data["day"] == 1
        assert data["domain"] == "PM-5M"
        assert data["event_count"] == 10
        assert data["trade_count"] == 5
        assert data["reflection_report_id"] == 1

    def test_bundle_creates_contracts_json(self, tmp_path):
        """contracts.json contains contract validation results."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        violation = ContractViolation(
            contract_name="DRY_RUN_ENFORCED",
            severity="CRITICAL",
            detail="test",
            timestamp="2024-01-01T00:00:00",
        )
        report = SessionReport(
            day=1,
            domain="PM-5M",
            event_count=0,
            trade_count=0,
            reflection_report_id=None,
            contract_results=[violation],
        )
        bundler = EvidenceBundler(db, output_base=str(tmp_path))
        bundle_path = bundler.bundle(report)

        contracts_file = bundle_path / "contracts.json"
        assert contracts_file.exists()
        data = json.loads(contracts_file.read_text())
        assert len(data) == 1
        assert data[0]["contract_name"] == "DRY_RUN_ENFORCED"

    def test_bundle_directory_naming(self, tmp_path):
        """Bundle directory is {output_base}/paper_trading/dia-NNN/."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))
        report = SessionReport(
            day=5,
            domain="PM-5M",
            event_count=0,
            trade_count=0,
            reflection_report_id=None,
        )

        bundle_path = bundler.bundle(report)
        assert bundle_path.name == "dia-005"
        assert bundle_path.parent.name == "paper_trading"

    def test_bundle_output_is_deterministic(self, tmp_path):
        """Two bundles for same day produce identical checksums."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))
        report = self._make_report()

        path1 = bundler.bundle(report)
        path2 = bundler.bundle(report)

        manifest1 = json.loads((path1 / "manifest.json").read_text())
        manifest2 = json.loads((path2 / "manifest.json").read_text())
        assert manifest1["artifact_checksums"] == manifest2["artifact_checksums"]


class TestEvidenceBundlerRegenerate:
    """EvidenceBundler.regenerate_bundle() — reconstruction from DB."""

    def _seed_day(self, db: sqlite_utils.Database, day: int = 1, domain: str = "PM-5M"):
        """Insert minimal data for a completed day."""
        now = datetime.now(UTC).isoformat()
        # Insert reflection report
        db.execute(
            """INSERT INTO reflection_reports
               (scope, domain, mode, period_start, period_end, report_data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ["daily", domain, "dry_run", now, now, '{"test": true}', now],
        )
        # Insert some events
        for i in range(3):
            db.execute(
                """INSERT INTO event_store
                   (event_id, market_id, price, volume, timestamp, event_type, raw_payload, captured_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [f"evt-{day}-{i}", "0x123", "100.0", "10.0", now, "tick", "{}", now],
            )
        # Insert trades
        db["trades"].insert({
            "id": f"t-{day}-1",
            "signal_id": f"s-{day}-1",
            "position_id": f"p-{day}-1",
            "action": "OPEN",
            "price": "100.0",
            "size": "1.0",
            "timestamp": now,
            "dry_run": 1,
        })

    def test_regenerate_complete_day(self, tmp_path):
        """Regenerated bundle for a complete day produces valid manifest."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        self._seed_day(db, day=1)
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        bundle_path = bundler.regenerate_bundle(1, "PM-5M")
        assert bundle_path.exists()
        manifest = json.loads((bundle_path / "manifest.json").read_text())
        assert manifest["day"] == 1
        assert manifest["domain"] == "PM-5M"
        assert len(manifest["artifact_checksums"]) == 2

    def test_regenerate_incomplete_day_fails(self, tmp_path):
        """Regenerating bundle for incomplete day raises ValueError."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        with pytest.raises(ValueError, match="incomplete"):
            bundler.regenerate_bundle(99, "PM-5M")

    def test_regenerate_deterministic(self, tmp_path):
        """Two regenerations for same day produce same checksums."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        self._seed_day(db, day=1)
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        path1 = bundler.regenerate_bundle(1, "PM-5M")
        path2 = bundler.regenerate_bundle(1, "PM-5M")
        m1 = json.loads((path1 / "manifest.json").read_text())
        m2 = json.loads((path2 / "manifest.json").read_text())
        assert m1["artifact_checksums"] == m2["artifact_checksums"]
