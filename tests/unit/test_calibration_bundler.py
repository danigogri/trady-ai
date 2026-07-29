"""Tests for calibration evidence bundling.

Verifies cal-NNN directory structure, manifest SHA-256, regenerability.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import sqlite_utils

from trady_ai.core.persistence import init_core_tables
from trady_ai.reflection.calibration.models import AdoptedStateSpace, EvidenceReport


def _make_db() -> sqlite_utils.Database:
    """Create a fresh in-memory DB with core tables."""
    db = sqlite_utils.Database(memory=True)
    init_core_tables(db)
    from trady_ai.reflection.calibration.persistence import init_calibration_tables

    init_calibration_tables(db)
    return db


def _find_file(bundle_path: Path, prefix: str) -> Path:
    """Find a timestamped file in the bundle directory by prefix."""
    matches = list(bundle_path.glob(f"{prefix}-*.json"))
    assert len(matches) == 1, f"Expected 1 {prefix}-*.json, found {len(matches)}"
    return matches[0]


def _read_json(bundle_path: Path, prefix: str) -> dict:
    """Find and parse a timestamped JSON file in the bundle directory."""
    return json.loads(_find_file(bundle_path, prefix).read_text())


class TestCalibrationBundler:
    """Calibration bundle structure and determinism."""

    def test_bundle_creates_cal_directory(self, tmp_path):
        """Bundle directory is paper_trading/cal-NNN/."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        report = EvidenceReport(
            aic=100.0,
            bic=120.0,
            num_states=3,
            num_observations=90,
        )
        adoption = AdoptedStateSpace(
            domain="PM-5M",
            strategy_name="markov_persistence",
            states=3,
            generator="directional",
        )
        bundle_path = bundler.calibration_bundle(report, adoption, day=5)

        assert bundle_path.exists()
        assert bundle_path.name == "cal-005"
        assert bundle_path.parent.name == "paper_trading"

    def test_bundle_contains_all_four_files(self, tmp_path):
        """cal-NNN/ contains evidence_report, adopted_config, provenance, manifest."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        report = EvidenceReport(
            aic=100.0,
            bic=120.0,
            num_states=3,
            num_observations=90,
        )
        adoption = AdoptedStateSpace(
            domain="PM-5M",
            strategy_name="markov_persistence",
            states=3,
            generator="directional",
        )
        bundle_path = bundler.calibration_bundle(report, adoption, day=5)

        assert len(list(bundle_path.glob("evidence_report-*.json"))) == 1
        assert len(list(bundle_path.glob("adopted_config-*.json"))) == 1
        assert len(list(bundle_path.glob("provenance-*.json"))) == 1
        assert len(list(bundle_path.glob("manifest-*.json"))) == 1

    def test_manifest_contains_sha256_checksums(self, tmp_path):
        """manifest.json has SHA-256 of the other three files."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        report = EvidenceReport(aic=100.0, bic=120.0, num_states=3)
        adoption = AdoptedStateSpace(
            domain="PM-5M",
            strategy_name="markov_persistence",
            states=3,
            generator="directional",
        )
        bundle_path = bundler.calibration_bundle(report, adoption, day=5)

        manifest = _read_json(bundle_path, "manifest")
        assert "artifact_checksums" in manifest

        checksums = manifest["artifact_checksums"]
        assert len(checksums) == 3  # evidence_report, adopted_config, provenance

        # Verify each checksum matches actual file content
        for filename, expected_checksum in checksums.items():
            file_path = bundle_path / filename
            assert file_path.exists(), f"File {filename} not found"
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            assert actual == expected_checksum, (
                f"Checksum mismatch for {filename}"
            )

    def test_bundle_evidence_report_content(self, tmp_path):
        """evidence_report JSON matches EvidenceReport data."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        report = EvidenceReport(
            aic=245.3,
            bic=310.7,
            conditional_entropy=1.2,
            num_states=3,
        )
        adoption = AdoptedStateSpace(
            domain="PM-5M",
            strategy_name="markov_persistence",
            states=3,
            generator="directional",
        )
        bundle_path = bundler.calibration_bundle(report, adoption, day=5)

        data = _read_json(bundle_path, "evidence_report")
        assert data["aic"] == 245.3
        assert data["bic"] == 310.7
        assert data["conditional_entropy"] == 1.2
        assert data["num_states"] == 3

    def test_bundle_adopted_config_content(self, tmp_path):
        """adopted_config JSON matches AdoptedStateSpace data."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        report = EvidenceReport(num_states=4)
        adoption = AdoptedStateSpace(
            domain="PM-5M",
            strategy_name="markov_persistence",
            states=4,
            generator="volatility",
            evidence_report_ref="abc123sha256",
            operator="test_operator",
            reason="Testing adoption",
        )
        bundle_path = bundler.calibration_bundle(report, adoption, day=10)

        data = _read_json(bundle_path, "adopted_config")
        assert data["domain"] == "PM-5M"
        assert data["states"] == 4
        assert data["generator"] == "volatility"
        assert data["evidence_report_ref"] == "abc123sha256"
        assert data["operator"] == "test_operator"
        assert data["reason"] == "Testing adoption"

    def test_provenance_contains_hostname_timestamp(self, tmp_path):
        """provenance.json has hostname, timestamp."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        report = EvidenceReport(num_states=3)
        adoption = AdoptedStateSpace(
            domain="PM-5M",
            strategy_name="markov_persistence",
            states=3,
            generator="directional",
        )
        bundle_path = bundler.calibration_bundle(report, adoption, day=5)

        data = _read_json(bundle_path, "provenance")
        assert "hostname" in data
        assert "timestamp" in data

    def test_deterministic_bundle_output(self, tmp_path):
        """Two bundles for same day produce same checksums."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        report = EvidenceReport(
            aic=100.0,
            bic=120.0,
            transition_counts=[[10, 2], [3, 15]],
            num_states=2,
        )
        adoption = AdoptedStateSpace(
            domain="PM-5M",
            strategy_name="markov_persistence",
            states=2,
            generator="directional",
        )

        path1 = bundler.calibration_bundle(report, adoption, day=1)
        path2 = bundler.calibration_bundle(report, adoption, day=1)

        m1 = _read_json(path1, "manifest")
        m2 = _read_json(path2, "manifest")
        assert m1["artifact_checksums"] == m2["artifact_checksums"]

    def test_separate_from_session_bundles(self, tmp_path):
        """Calibration bundles use cal-NNN, not dia-NNN."""
        from trady_ai.paper_trading.bundler import EvidenceBundler

        db = _make_db()
        bundler = EvidenceBundler(db, output_base=str(tmp_path))

        report = EvidenceReport(num_states=3)
        adoption = AdoptedStateSpace(
            domain="PM-5M",
            strategy_name="markov_persistence",
            states=3,
            generator="directional",
        )
        bundle_path = bundler.calibration_bundle(report, adoption, day=5)

        # Calibration bundles go to cal-NNN
        assert bundle_path.name == "cal-005"

        # Session bundles go to dia-NNN
        from trady_ai.paper_trading.models import SessionReport

        session_report = SessionReport(
            day=5,
            session_number=1,
            domain="PM-5M",
            event_count=10,
            trade_count=5,
            reflection_report_id=1,
        )
        session_path = bundler.bundle(session_report)
        assert session_path.name == "sesion-001"
        assert session_path.parent.name == "dia-005"
        assert session_path.parent.parent == bundle_path.parent  # both under paper_trading/
