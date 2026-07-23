"""Persistence helpers for the Calibration Framework.

Provides:
    - save_evidence_report: Persist an EvidenceReport to the DB.
    - load_transition_counts: Load transition counts from strategy_snapshots.
    - save_adoption: Persist an adoption record to calibration_adoptions.
    - load_adoptions: Query adoption history for a domain/strategy.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import sqlite_utils

from trady_ai.reflection.calibration.models import AdoptedStateSpace, EvidenceReport


def load_transition_counts(
    db: sqlite_utils.Database,
    domain: str,
    strategy_name: str,
    tick_number: int | None = None,
) -> dict[str, Any] | None:
    """Load transition counts and state sequence info from strategy_snapshots.

    Args:
        db: Database instance.
        domain: Market domain (e.g. ``"PM-5M"``).
        strategy_name: Strategy name (e.g. ``"markov_persistence"``).
        tick_number: Optional specific tick. Loads latest if ``None``.

    Returns:
        Dict with keys ``transition_counts`` (list of lists),
        ``state_counts`` (list), ``state_space_size`` (int), ``tick_number``
        (int), or ``None`` if no snapshot exists.
    """
    if tick_number is not None:
        rows = list(
            db.query(
                "SELECT * FROM strategy_snapshots "
                "WHERE strategy_name = ? AND domain = ? AND tick_number = ?",
                [strategy_name, domain, tick_number],
            )
        )
    else:
        rows = list(
            db.query(
                "SELECT * FROM strategy_snapshots "
                "WHERE strategy_name = ? AND domain = ? "
                "ORDER BY tick_number DESC LIMIT 1",
                [strategy_name, domain],
            )
        )

    if not rows:
        return None

    row = rows[0]
    return {
        "transition_counts": json.loads(row["transition_counts"]),
        "state_counts": json.loads(row["state_counts"]),
        "state_space_size": row.get("state_space_size", 3),
        "tick_number": row["tick_number"],
    }


def load_state_sequence(
    db: sqlite_utils.Database,
    domain: str,
    strategy_name: str,
    limit: int = 10000,
) -> list[int]:
    """Load state sequence from execution_log for a domain/strategy.

    Args:
        db: Database instance.
        domain: Market domain.
        strategy_name: Strategy name.
        limit: Max number of state entries to load.

    Returns:
        List of state indices (integers), in chronological order.
    """
    # We reconstruct state sequence from strategy_snapshots by loading
    # snapshots in order and inferring transitions from transition_counts
    # differences. A simpler approach: load available state snapshots
    # and build the sequence from the cumulative counts.
    #
    # For now, we extract the state index from the execution_log state column
    # which stores the classified state label (e.g. "UP", "DOWN").
    rows = list(
        db.query(
            "SELECT state FROM execution_log "
            "ORDER BY tick_number ASC LIMIT ?",
            [limit],
        )
    )

    if not rows:
        return []

    # Try loading state labels from the latest snapshot
    snapshot = load_transition_counts(db, domain, strategy_name)
    if snapshot is None:
        return []

    state_space_size = snapshot["state_space_size"]

    # Map labels to indices using known generators
    indices: list[int] = []
    for row in rows:
        label = row["state"]
        idx = _label_to_index(label, state_space_size)
        if idx is not None:
            indices.append(idx)

    return indices


def _label_to_index(label: str, state_space_size: int) -> int | None:
    """Map a state label string to its index.

    Supports the known label sets from DirectionalStateGenerator (|S|=3)
    and VolatilityStateGenerator (|S|=3). For arbitrary state spaces,
    labels are expected to be integer strings.
    """
    # Try integer labels first
    try:
        idx = int(label)
        if 0 <= idx < state_space_size:
            return idx
    except (ValueError, TypeError):
        pass

    # Known label maps for |S|=3
    if state_space_size == 3:
        directional_labels = {"UP": 0, "DOWN": 1, "NEUTRAL": 2}
        volatility_labels = {"HIGH": 0, "LOW": 1, "STABLE": 2}
        if label in directional_labels:
            return directional_labels[label]
        if label in volatility_labels:
            return volatility_labels[label]

    return None


def save_evidence_report(
    db: sqlite_utils.Database,
    report: EvidenceReport,
    domain: str,
    strategy_name: str,
) -> int:
    """Persist an EvidenceReport to the calibration_evidence table.

    Args:
        db: Database instance.
        report: The EvidenceReport to persist.
        domain: Market domain.
        strategy_name: Strategy name.

    Returns:
        int: The auto-generated report ID.
    """
    now = datetime.now(UTC).isoformat()
    cursor = db.execute(
        "INSERT INTO calibration_evidence "
        "(domain, strategy_name, aic, bic, markov_statistic, markov_p_value, "
        "markov_df, markov_reject_null, conditional_entropy, "
        "state_persistence, num_states, num_observations, "
        "evidence_data, computed_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            domain,
            strategy_name,
            report.aic,
            report.bic,
            report.markov_test.get("statistic", 0.0),
            report.markov_test.get("p_value", 1.0),
            report.markov_test.get("df", 0),
            1 if report.markov_test.get("reject_null", False) else 0,
            report.conditional_entropy,
            json.dumps(report.state_persistence),
            report.num_states,
            report.num_observations,
            json.dumps({
                "transition_counts": report.transition_counts,
                "aic": report.aic,
                "bic": report.bic,
                "markov_test": report.markov_test,
                "state_persistence": report.state_persistence,
                "conditional_entropy": report.conditional_entropy,
            }),
            report.computed_at,
            now,
        ],
    )
    rid = cursor.lastrowid
    return int(rid) if rid is not None else 0


def save_adoption(
    db: sqlite_utils.Database,
    adoption: AdoptedStateSpace,
) -> int:
    """Persist an adoption record to the calibration_adoptions table.

    Args:
        db: Database instance.
        adoption: The adoption record to persist.

    Returns:
        int: The auto-generated adoption ID.
    """
    cursor = db.execute(
        "INSERT INTO calibration_adoptions "
        "(domain, strategy_name, states, generator, evidence_report_ref, "
        "operator, adopted_at, reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            adoption.domain,
            adoption.strategy_name,
            adoption.states,
            adoption.generator,
            adoption.evidence_report_ref,
            adoption.operator,
            adoption.adopted_at,
            adoption.reason,
        ],
    )
    aid = cursor.lastrowid
    return int(aid) if aid is not None else 0


def load_adoptions(
    db: sqlite_utils.Database,
    domain: str,
    strategy_name: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Load adoption history for a domain.

    Args:
        db: Database instance.
        domain: Market domain.
        strategy_name: Optional strategy name filter.
        limit: Max rows to return.

    Returns:
        List of adoption row dicts, newest first.
    """
    if strategy_name:
        rows = list(
            db.query(
                "SELECT * FROM calibration_adoptions "
                "WHERE domain = ? AND strategy_name = ? "
                "ORDER BY id DESC LIMIT ?",
                [domain, strategy_name, limit],
            )
        )
    else:
        rows = list(
            db.query(
                "SELECT * FROM calibration_adoptions "
                "WHERE domain = ? ORDER BY id DESC LIMIT ?",
                [domain, limit],
            )
        )
    return rows


def init_calibration_tables(db: sqlite_utils.Database) -> None:
    """Create calibration tables if they don't exist. Idempotent.

    Creates: calibration_evidence, calibration_adoptions
    with corresponding indexes.
    """
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS calibration_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            aic REAL NOT NULL DEFAULT 0.0,
            bic REAL NOT NULL DEFAULT 0.0,
            markov_statistic REAL NOT NULL DEFAULT 0.0,
            markov_p_value REAL NOT NULL DEFAULT 1.0,
            markov_df INTEGER NOT NULL DEFAULT 0,
            markov_reject_null INTEGER NOT NULL DEFAULT 0,
            conditional_entropy REAL NOT NULL DEFAULT 0.0,
            state_persistence TEXT NOT NULL DEFAULT '{}',
            num_states INTEGER NOT NULL DEFAULT 0,
            num_observations INTEGER NOT NULL DEFAULT 0,
            evidence_data TEXT NOT NULL DEFAULT '{}',
            computed_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_calibration_evidence_domain
        ON calibration_evidence(domain, strategy_name)
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS calibration_adoptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            states INTEGER NOT NULL,
            generator TEXT NOT NULL,
            evidence_report_ref TEXT NOT NULL DEFAULT '',
            operator TEXT NOT NULL DEFAULT '',
            adopted_at TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT ''
        )
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_calibration_adoptions_domain
        ON calibration_adoptions(domain, strategy_name)
        """
    )
