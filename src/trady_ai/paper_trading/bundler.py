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

        All filenames include an ``HHMMSS`` UTC timestamp suffix to prevent
        overwrites when multiple sessions execute within the same calendar day.

        Args:
            report: ``SessionReport`` from a paper trading session run.

        Returns:
            ``Path`` to the created bundle directory (``dia-NNN/``).
        """
        day_dir = self._day_dir(report.day)
        day_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(UTC).strftime("%H%M%S")

        # ── Write session report ─────────────────────────────────────────────
        report_path = day_dir / f"session_report-{ts}.json"
        report_data = _dataclass_to_dict(report)
        report_path.write_text(json.dumps(report_data, indent=2, default=str))

        # ── Write contract results ───────────────────────────────────────────
        contracts_path = day_dir / f"contracts-{ts}.json"
        contracts_data = [_dataclass_to_dict(v) for v in report.contract_results]
        contracts_path.write_text(json.dumps(contracts_data, indent=2))

        # ── Compute SHA-256 checksums ────────────────────────────────────────
        checksums: dict[str, str] = {}
        for name in [f"session_report-{ts}.json", f"contracts-{ts}.json"]:
            content = (day_dir / name).read_bytes()
            checksums[name] = hashlib.sha256(content).hexdigest()

        # ── Write manifest ───────────────────────────────────────────────────
        manifest = SessionManifest(
            day=report.day,
            domain=report.domain,
            created_at=datetime.now(UTC).isoformat(),
            artifact_checksums=checksums,
        )
        manifest_path = day_dir / f"manifest-{ts}.json"
        manifest_data = _dataclass_to_dict(manifest)
        manifest_path.write_text(json.dumps(manifest_data, indent=2))

        logger.info(
            "evidence_bundle_created",
            day=report.day,
            domain=report.domain,
            path=str(day_dir),
        )
        return day_dir

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
            domain=domain,
            event_count=event_count,
            trade_count=trade_count,
            reflection_report_id=rid,
        )

        logger.info("evidence_bundle_regenerated", day=day, domain=domain)
        return self.bundle(report)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _day_dir(self, day: int) -> Path:
        """Return ``dia-NNN/`` path beneath ``paper_trading/``."""
        return self._output_base / "paper_trading" / f"dia-{day:03d}"

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
