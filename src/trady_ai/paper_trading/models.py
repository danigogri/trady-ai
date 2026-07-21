"""Paper trading data models.

Defines the core types for session lifecycle, contract violations,
and evidence bundling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SessionState(StrEnum):
    """Finite state machine states for a paper trading session."""

    IDLE = "idle"
    PRE_FLIGHT = "pre_flight"
    CAPTURING = "capturing"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    VERIFYING = "verifying"
    BUNDLING = "bundling"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ContractViolation:
    """Result of a single operational contract check.

    Attributes:
        contract_name: Machine-readable contract identifier
            (e.g. ``"DRY_RUN_ENFORCED"``).
        severity: ``"CRITICAL"`` halts the session; ``"WARNING"`` is logged only.
        detail: Human-readable description of the violation.
        timestamp: ISO-8601 timestamp of when the violation was detected.
    """

    contract_name: str
    severity: str  # "CRITICAL" | "WARNING"
    detail: str
    timestamp: str


@dataclass
class SessionReport:
    """Result of a single paper trading session run.

    Attributes:
        day: Day number in the 30-day lifecycle (1-30).
        domain: Market domain (e.g. ``"PM-5M"``).
        event_count: Number of events captured during the session.
        trade_count: Number of trades executed.
        reflection_report_id: FK to ``reflection_reports.id``, or ``None``
            if reflection was not completed.
        contract_results: List of contract violations found (empty = all passed).
        stage_timestamps: Mapping of stage name → ISO-8601 timestamp.
        calibration_state: Current calibration readiness state.
    """

    day: int
    domain: str
    event_count: int
    trade_count: int
    reflection_report_id: int | None
    contract_results: list[ContractViolation] = field(default_factory=list)
    stage_timestamps: dict[str, str] = field(default_factory=dict)
    calibration_state: str = "not_ready"
    market_ids: list[str] = field(default_factory=list)


@dataclass
class SessionManifest:
    """Evidence bundle manifest for a completed session day.

    Attributes:
        day: Day number in the 30-day lifecycle.
        domain: Market domain.
        created_at: ISO-8601 timestamp of bundle creation.
        artifact_checksums: Mapping of artifact filename → SHA-256 hex digest.
    """

    day: int
    domain: str
    created_at: str
    artifact_checksums: dict[str, str] = field(default_factory=dict)
