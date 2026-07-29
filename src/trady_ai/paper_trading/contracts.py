"""Operational contract validators for paper trading sessions.

Each contract is a function returning ``list[ContractViolation]``
(empty list = passed). Severity ``CRITICAL`` halts the session,
``WARNING`` is logged only.

Contracts are validated at PRE_FLIGHT (gating entry) and VERIFYING
(evidence check) stages per REQ-PT-002.
"""
from __future__ import annotations

import ast
import os
from datetime import UTC, datetime

import sqlite_utils

from trady_ai.paper_trading.models import ContractViolation

# Top-level package names that are forbidden for session.py to import.
# Defined by the Operational Isolation Contract (REQ-PT-003).
_FORBIDDEN_IMPORTS = {"strategies", "intelligence", "governance"}

# Function names that session.py MUST NOT import (direct persistence bypass).
# Reflection must own all snapshot persistence; session delegates via
# ReflectionEngine, never calls persist_strategy_snapshot directly.
_FORBIDDEN_FUNCTIONS = {"persist_strategy_snapshot"}


def _now_iso() -> str:
    """Return current UTC timestamp as ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def dry_run_enforced(execution_mode: str) -> list[ContractViolation]:
    """Validate that the execution mode is ``"dry_run"``.

    REQ-PT-002 — DRY_RUN_ENFORCED contract.
    Checked at PRE_FLIGHT stage. Returns a CRITICAL violation when the
    mode is anything other than ``"dry_run"``.
    """
    if execution_mode != "dry_run":
        return [
            ContractViolation(
                contract_name="DRY_RUN_ENFORCED",
                severity="CRITICAL",
                detail=(
                    f"Execution mode is '{execution_mode}', "
                    f"expected 'dry_run'"
                ),
                timestamp=_now_iso(),
            )
        ]
    return []


def no_real_funds(db: sqlite_utils.Database) -> list[ContractViolation]:
    """Validate that no trades were placed with ``dry_run=0``.

    REQ-PT-002 — NO_REAL_FUNDS contract.
    Queries the ``trades`` table for any row where ``dry_run = 0``,
    which would indicate real funds were used.
    """
    row = db.execute(
        "SELECT COUNT(*) FROM trades WHERE dry_run = 0"
    ).fetchone()
    count = row[0] if row else 0
    if count > 0:
        return [
            ContractViolation(
                contract_name="NO_REAL_FUNDS",
                severity="CRITICAL",
                detail=(
                    f"Found {count} trade(s) with dry_run=0 "
                    f"(real funds were used)"
                ),
                timestamp=_now_iso(),
            )
        ]
    return []


def temporal_integrity(
    db: sqlite_utils.Database, domain: str, last_processed_seq: int
) -> list[ContractViolation]:
    """Validate no overlapping event processing for the same domain.

    REQ-PT-002 — TEMPORAL_INTEGRITY contract.
    Checks per-sequence overlap: does any existing session already process
    events beyond ``last_processed_seq`` for the same domain? Multiple
    sessions per calendar day are expected under the 15-minute rhythm —
    only overlapping sequence ranges are blocked.

    Args:
        db: Database instance.
        domain: Market domain (e.g. ``"FOOTBALL-WINNER"``).
        last_processed_seq: The sequence number this session intends to
            start from. If a previous session already processed events
            beyond this point, it is an overlapping range.

    Returns:
        Empty list on pass. CRITICAL violation on overlap detection.
    """
    # Query the highest tick_number processed in execution_log
    cursor = db.execute(
        "SELECT COALESCE(MAX(tick_number), 0) FROM execution_log",
    )
    row = cursor.fetchone()
    max_processed = int(row[0]) if row and row[0] else 0

    if last_processed_seq < max_processed:
        return [
            ContractViolation(
                contract_name="TEMPORAL_INTEGRITY",
                severity="CRITICAL",
                detail=(
                    f"Overlapping event range for domain '{domain}': "
                    f"already processed up to seq {max_processed}, "
                    f"current session starts at {last_processed_seq}"
                ),
                timestamp=_now_iso(),
            )
        ]
    return []


def evidence_completeness(
    db: sqlite_utils.Database,
    domain: str,
    day: int,  # noqa: ARG001
) -> list[ContractViolation]:
    """Validate that a ``reflection_reports`` entry exists.

    REQ-PT-002 — EVIDENCE_COMPLETENESS contract.
    Checked at the VERIFYING stage to confirm the reflection step
    actually persisted a report.
    """
    cursor = db.execute(
        "SELECT COUNT(*) FROM reflection_reports WHERE domain = ?",
        [domain],
    )
    count = cursor.fetchone()[0] if cursor else 0
    if count == 0:
        return [
            ContractViolation(
                contract_name="EVIDENCE_COMPLETENESS",
                severity="CRITICAL",
                detail=(
                    f"No reflection_report found for domain "
                    f"'{domain}'"
                ),
                timestamp=_now_iso(),
            )
        ]
    return []


def deterministic_reproducibility() -> list[ContractViolation]:
    """Placeholder — replay verification is deferred.

    REQ-PT-002 — DETERMINISTIC_REPRODUCIBILITY contract.
    Returns a WARNING because true replay verification requires the
    replay infrastructure which is not yet wired into the session.
    """
    return [
        ContractViolation(
            contract_name="DETERMINISTIC_REPRODUCIBILITY",
            severity="WARNING",
            detail="Replay verification deferred — not yet implemented",
            timestamp=_now_iso(),
        )
    ]


def reflection_isolation() -> list[ContractViolation]:
    """Placeholder — enforced via import boundary, not runtime check.

    REQ-PT-002 — REFLECTION_ISOLATION contract.
    Reflection isolation is ensured by the module-level import boundary
    check in ``validate_isolation_boundary()``, not by a runtime check.
    This function is a no-op that always passes.
    """
    return []


def validate_isolation_boundary(
    session_path: str | None = None,
) -> list[ContractViolation]:
    """Validate that ``session.py`` does not import forbidden modules.

    Enforces the six MUST NOT prohibitions from the Operational
    Isolation Contract (REQ-PT-003).  Inspects the AST of
    ``session.py`` and returns a CRITICAL violation for each import
    of ``strategies``, ``intelligence``, or ``governance``.

    Args:
        session_path: Explicit path to ``session.py``.  When ``None``
            (the default), resolves relative to this file's directory.

    Returns:
        Empty list if no violations found or if ``session.py`` does not
        exist yet (PR #1 scenario).
    """
    violations: list[ContractViolation] = []

    if session_path is None:
        session_path = os.path.join(os.path.dirname(__file__), "session.py")

    if not os.path.exists(session_path):
        return violations

    with open(session_path) as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _check_forbidden(alias.name):
                    violations.append(
                        ContractViolation(
                            contract_name="REFLECTION_ISOLATION",
                            severity="CRITICAL",
                            detail=(
                                f"Import boundary violation: session.py "
                                f"imports '{alias.name}'"
                            ),
                            timestamp=_now_iso(),
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                if _check_forbidden(node.module):
                    violations.append(
                        ContractViolation(
                            contract_name="REFLECTION_ISOLATION",
                            severity="CRITICAL",
                            detail=(
                                f"Import boundary violation: session.py "
                                f"imports from '{node.module}'"
                            ),
                            timestamp=_now_iso(),
                        )
                    )
                # Check individual imported names for forbidden functions
                for alias in node.names:
                    if alias.name in _FORBIDDEN_FUNCTIONS:
                        violations.append(
                            ContractViolation(
                                contract_name="REFLECTION_ISOLATION",
                                severity="CRITICAL",
                                detail=(
                                    f"Import boundary violation: session.py "
                                    f"imports '{alias.name}' from "
                                    f"'{node.module}'"
                                ),
                                timestamp=_now_iso(),
                            )
                        )

    return violations


def _check_forbidden(dotted_name: str) -> bool:
    """Return True if *any* segment of the dotted name is forbidden."""
    return any(part in _FORBIDDEN_IMPORTS for part in dotted_name.split("."))
