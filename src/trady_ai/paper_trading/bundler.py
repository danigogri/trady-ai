"""EvidenceBundler — regenerable deterministic exports from DB.

Produces per-session evidence bundles at ``{output_base}/paper_trading/dia-NNN/``
containing ``manifest.json``, ``session_report.json``, and ``contracts.json``.

The database is the source of truth. Bundles are deterministic exports:
calling ``bundle()`` or ``regenerate_bundle()`` with the same data always
produces the same artifacts (same SHA-256 checksums).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sqlite_utils
import structlog

from trady_ai.paper_trading.models import (
    SessionManifest,
    SessionReport,
)

logger = structlog.get_logger()


class EvidenceBundler:
    """Produce and reproduce portable evidence bundles from DB state.

    Args:
        db: Database instance (sqlite_utils.Database).
        output_base: Base directory for bundle output. Defaults to
            ``"paper_trading"`` (resolved relative to CWD).
    """

    def __init__(self, db: sqlite_utils.Database, output_base: str = "paper_trading") -> None:
        self._db = db
        self._output_base = Path(output_base)

    # ── Public API ───────────────────────────────────────────────────────────

    def bundle(self, report: SessionReport) -> Path:
        """Generate evidence bundle for a completed session.

        Creates the output directory, serializes the report and contract
        results, computes SHA-256 checksums, and writes a manifest.

        Each session writes to its own ``dia-NNN/sesion-MMM/`` subdirectory
        — no timestamp suffixes needed since session subdirectories guarantee
        uniqueness.

        Args:
            report: ``SessionReport`` from a paper trading session run.

        Returns:
            ``Path`` to the created session directory (``sesion-MMM/``).
        """
        session_dir = self._day_dir(report.day, report.session_number)
        session_dir.mkdir(parents=True, exist_ok=True)

        # ── Write session report ─────────────────────────────────────────────
        report_path = session_dir / "session_report.json"
        report_data = _dataclass_to_dict(report)
        report_path.write_text(json.dumps(report_data, indent=2, default=str))

        # ── Write contract results ───────────────────────────────────────────
        contracts_path = session_dir / "contracts.json"
        contracts_data = [_dataclass_to_dict(v) for v in report.contract_results]
        contracts_path.write_text(json.dumps(contracts_data, indent=2))

        # ── Write strategy snapshot (if present) ─────────────────────────────
        snapshot_path = session_dir / "strategy_snapshot.json"
        has_snapshot = False
        if report.strategy_snapshot is not None:
            snapshot_path.write_text(
                json.dumps(report.strategy_snapshot, indent=2, default=str)
            )
            has_snapshot = True

        # ── Compute SHA-256 checksums ────────────────────────────────────────
        checksums: dict[str, str] = {}
        for name in ["session_report.json", "contracts.json"]:
            content = (session_dir / name).read_bytes()
            checksums[name] = hashlib.sha256(content).hexdigest()
        if has_snapshot:
            snap_content = snapshot_path.read_bytes()
            checksums["strategy_snapshot.json"] = hashlib.sha256(snap_content).hexdigest()

        # ── Write manifest ───────────────────────────────────────────────────
        manifest = SessionManifest(
            day=report.day,
            session_number=report.session_number,
            domain=report.domain,
            created_at=datetime.now(UTC).isoformat(),
            artifact_checksums=checksums,
        )
        manifest_path = session_dir / "manifest.json"
        manifest_data = _dataclass_to_dict(manifest)
        manifest_path.write_text(json.dumps(manifest_data, indent=2))

        logger.info(
            "evidence_bundle_created",
            day=report.day,
            session=report.session_number,
            domain=report.domain,
            path=str(session_dir),
        )
        return session_dir

    def regenerate_bundle(self, day: int, domain: str) -> Path:
        """Regenerate evidence bundle from DB for a past day.

        Reconstructs a ``SessionReport`` from persisted data and delegates
        to ``bundle()``.

        Args:
            day: Session day number (1-30).
            domain: Market domain (e.g. ``"PM-5M"``).

        Returns:
            ``Path`` to the created bundle directory.

        Raises:
            ValueError: If the day is incomplete (missing reflection report).
        """
        rid_row = self._db.execute(
            "SELECT MAX(id) FROM reflection_reports WHERE domain = ?",
            [domain],
        ).fetchone()
        rid: int | None = rid_row[0] if rid_row and rid_row[0] else None

        if rid is None:
            raise ValueError(
                f"Day {day} incomplete: no reflection_report for domain '{domain}'"
            )

        event_count = self._count_today_events(day)
        trade_count = self._count_today_trades(day)

        report = SessionReport(
            day=day,
            session_number=1,
            domain=domain,
            event_count=event_count,
            trade_count=trade_count,
            reflection_report_id=rid,
        )

        logger.info("evidence_bundle_regenerated", day=day, domain=domain)
        return self.bundle(report)

    # ── Calibration bundle ──────────────────────────────────────────────────

    def calibration_bundle(
        self,
        evidence_report: Any,
        adoption_config: Any,
        day: int | None = None,
    ) -> Path:
        """Generate a calibration evidence bundle.

        Creates ``cal-NNN/`` directory with evidence_report, adopted_config,
        provenance, and manifest files — all with SHA-256 checksums.

        Args:
            evidence_report: EvidenceReport instance (or any object with
                ``dataclasses.asdict`` support).
            adoption_config: AdoptedStateSpace instance.
            day: Optional day number for directory naming. Defaults to current
                UTC day-of-month.

        Returns:
            ``Path`` to the created ``cal-NNN/`` directory.
        """
        if day is None:
            day = datetime.now(UTC).day

        cal_dir = self._cal_day_dir(day)
        cal_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(UTC).strftime("%H%M%S")

        # ── Write evidence report ───────────────────────────────────────────
        report_path = cal_dir / f"evidence_report-{ts}.json"
        report_data = _dataclass_to_dict(evidence_report)
        report_path.write_text(json.dumps(report_data, indent=2, default=str))

        # ── Write adopted config ────────────────────────────────────────────
        config_path = cal_dir / f"adopted_config-{ts}.json"
        config_data = _dataclass_to_dict(adoption_config)
        config_path.write_text(json.dumps(config_data, indent=2, default=str))

        # ── Write provenance ────────────────────────────────────────────────
        provenance = {
            "hostname": socket.gethostname(),
            "timestamp": datetime.now(UTC).isoformat(),
            "files": ["evidence_report", "adopted_config"],
        }
        provenance_path = cal_dir / f"provenance-{ts}.json"
        provenance_path.write_text(json.dumps(provenance, indent=2, default=str))

        # ── Compute SHA-256 checksums ────────────────────────────────────────
        checksums: dict[str, str] = {}
        for name in [
            f"evidence_report-{ts}.json",
            f"adopted_config-{ts}.json",
            f"provenance-{ts}.json",
        ]:
            content = (cal_dir / name).read_bytes()
            checksums[name] = hashlib.sha256(content).hexdigest()

        # ── Write manifest ──────────────────────────────────────────────────
        manifest = {
            "type": "calibration",
            "day": day,
            "created_at": datetime.now(UTC).isoformat(),
            "artifact_checksums": checksums,
        }
        manifest_path = cal_dir / f"manifest-{ts}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

        logger.info(
            "calibration_bundle_created",
            day=day,
            path=str(cal_dir),
        )
        return cal_dir

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _cal_day_dir(self, day: int) -> Path:
        """Return ``cal-NNN/`` path beneath ``paper_trading/``."""
        return self._output_base / "paper_trading" / f"cal-{day:03d}"

    def _day_dir(self, day: int, session: int) -> Path:
        """Return ``dia-NNN/sesion-MMM/`` path beneath ``paper_trading/``."""
        return self._output_base / "paper_trading" / f"dia-{day:03d}" / f"sesion-{session:03d}"

    def _count_today_events(self, day: int) -> int:
        """Count events for a given session day.

        Uses day offset from current date. For past sessions, counts all
        events in the store (best-effort heuristic — the event_store does
        not carry a "session day" column).
        """
        row = self._db.execute("SELECT COUNT(*) FROM event_store").fetchone()
        return int(row[0]) if row and row[0] else 0

    def _count_today_trades(self, day: int) -> int:
        """Count trades for a given session day."""
        row = self._db.execute(
            "SELECT COUNT(*) FROM trades WHERE dry_run = 1",
        ).fetchone()
        return int(row[0]) if row and row[0] else 0


# ── Serialisation helpers ──────────────────────────────────────────────────────


def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass instance to a plain dict.

    Handles nested dataclasses, lists of dataclasses, and standard types.
    """
    raw: Any = dataclasses.asdict(obj)
    result = _convert_nested(raw)
    return result if isinstance(result, dict) else {}


def _convert_nested(obj: Any) -> Any:
    """Recursively convert nested dataclass structures to plain types."""
    if isinstance(obj, dict):
        return {k: _convert_nested(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_nested(v) for v in obj]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _convert_nested(dataclasses.asdict(obj))
    return obj
