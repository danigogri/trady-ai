"""ReflectionEngine — orchestrator for reflection analysis.

Orchestrates the deterministic pipeline:
  scope resolution → outcome analysis → signal quality analysis →
  drift analysis → proposal generation → calibration gate check → persistence

All analyzers are injected via constructor (same pattern as ExecutionEngine).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import sqlite_utils

from trady_ai.reflection.models import DriftEvent, Proposal, ReflectionReport
from trady_ai.reflection.persistence import (
    get_reflection_config,
    save_drift_events,
    save_proposals,
    save_reflection_report,
    set_reflection_config,
)
from trady_ai.reflection.proposals.generator import ProposalGenerator

# Scope → timedelta mapping for time range resolution
_SCOPE_DELTAS: dict[str, timedelta] = {
    "session": timedelta(hours=1),
    "daily": timedelta(hours=24),
    "weekly": timedelta(days=7),
}

# Default minimum sessions for calibration evidence gate
_DEFAULT_MIN_SESSIONS = 30
# Default review threshold in days
_DEFAULT_REVIEW_THRESHOLD_DAYS = 30


class ReflectionEngine:
    """Orchestrates reflection analysis: analyzers → proposals → persistence.

    Constructor injection for all dependencies (per design ADR-1).

    Args:
        db: Database instance.
        outcome_analyzer: OutcomeAnalyzer instance.
        signal_quality_analyzer: SignalQualityAnalyzer instance.
        drift_analyzer: DriftAnalyzer instance.
        proposal_generator: ProposalGenerator instance.
    """

    def __init__(
        self,
        db: sqlite_utils.Database,
        outcome_analyzer: Any,
        signal_quality_analyzer: Any,
        drift_analyzer: Any,
        proposal_generator: ProposalGenerator,
        calibration_analyzer: Any = None,
    ) -> None:
        self._db = db
        self._outcome_analyzer = outcome_analyzer
        self._signal_quality_analyzer = signal_quality_analyzer
        self._drift_analyzer = drift_analyzer
        self._proposal_generator = proposal_generator
        self._calibration_analyzer = calibration_analyzer

    def reflect(
        self,
        scope: Literal["session", "daily", "weekly"],
        domain: str,
        mode: Literal["dry_run"],
        baseline_tick: int | None = None,
        comparison_tick: int | None = None,
        current_params: dict[str, float] | None = None,
        execution_result: Any | None = None,
    ) -> ReflectionReport:
        """Execute the full reflection pipeline.

        Args:
            scope: Time scope for analysis (session=1h, daily=24h, weekly=7d).
            domain: Market domain (e.g. ``"PM-5M"``).
            mode: Execution mode (only ``"dry_run"`` supported).
            baseline_tick: Optional baseline snapshot tick for drift comparison.
            comparison_tick: Optional comparison snapshot tick.
            current_params: Optional current parameter values for proposal
                generation.
            execution_result: Optional ``ExecutionResult`` from the execution
                engine. When provided, snapshot data is extracted and persisted
                via ``persist_snapshot()`` after analysis, before report assembly.

        Returns:
            ReflectionReport: Complete report with all analysis results.
        """
        # ── 1. Resolve time range ────────────────────────────────────────
        delta = _SCOPE_DELTAS.get(scope, timedelta(hours=1))
        end = datetime.now(UTC)
        start = end - delta
        start_str = start.isoformat()
        end_str = end.isoformat()

        # ── 2. Outcome analysis ──────────────────────────────────────────
        outcome_summary = self._outcome_analyzer.analyze(
            self._db, domain, start_str, end_str
        )

        # ── 3. Signal quality analysis ───────────────────────────────────
        signal_quality = self._signal_quality_analyzer.analyze(
            self._db, domain, start_str, end_str
        )

        # ── 4. Drift analysis (per strategy) ─────────────────────────────
        strategy_ids = self._get_strategy_ids(domain)
        all_drift_events: list[DriftEvent] = []
        for sid in strategy_ids:
            events = self._drift_analyzer.analyze(
                self._db,
                sid,
                domain,
                baseline_tick=baseline_tick,
                comparison_tick=comparison_tick,
            )
            all_drift_events.extend(events)

        # ── 5. Proposal generation ───────────────────────────────────────
        all_proposals: list[Proposal] = []
        if current_params is not None:
            for sid in strategy_ids:
                proposals = self._proposal_generator.generate(
                    sid, current_params, all_drift_events
                )
                all_proposals.extend(proposals)

        # ── 5.5 Calibration analysis (optional) ──────────────────────────
        evidence_report_dict: dict[str, Any] | None = None
        if self._calibration_analyzer is not None:
            try:
                for sid in strategy_ids:
                    er = self._calibration_analyzer.analyze(
                        self._db, domain, strategy_name=sid
                    )
                    evidence_report_dict = {
                        "strategy_name": sid,
                        "aic": er.aic,
                        "bic": er.bic,
                        "markov_test": er.markov_test,
                        "state_persistence": er.state_persistence,
                        "conditional_entropy": er.conditional_entropy,
                        "num_states": er.num_states,
                        "num_observations": er.num_observations,
                        "computed_at": er.computed_at,
                    }
            except Exception:
                evidence_report_dict = {"error": "calibration analysis failed"}

        # ── 5.6 Persist strategy snapshot from execution result ──────────
        if execution_result is not None:
            self.persist_snapshot(execution_result, domain=domain)

        # ── 6. Assemble report ───────────────────────────────────────────
        report = ReflectionReport(
            scope=scope,
            domain=domain,
            mode=mode,
            period_start=start,
            period_end=end,
            outcome_summary=outcome_summary,
            signal_quality=signal_quality,
            drift_events=all_drift_events,
            proposals=all_proposals,
            calibration_state=self._check_calibration_readiness(domain),
            evidence_report=evidence_report_dict,
            created_at=datetime.now(UTC),
        )

        # ── 7. Persist ──────────────────────────────────────────────────
        save_reflection_report(self._db, report)
        save_drift_events(self._db, all_drift_events)
        save_proposals(self._db, all_proposals)
        self._db.conn.commit()

        return report

    def _get_strategy_ids(self, domain: str) -> list[str]:
        """Return distinct strategy names for the given domain."""
        rows = self._db.query(
            "SELECT DISTINCT strategy_name FROM strategy_snapshots WHERE domain = ?",
            [domain],
        )
        return [r["strategy_name"] for r in rows]

    def _check_calibration_readiness(self, domain: str) -> str:
        """Check if domain is ready for calibration.

        Per design Calibration Gate section (RFC-004):
        - UNCALIBRATED → READY_FOR_CALIBRATION → CALIBRATED

        Dual gate (both required for ``ready_for_calibration``):
        1. Time gate: ``COUNT(DISTINCT DATE(period_start)) >= 30``
        2. Evidence gate: ``COUNT(*) >= min_sessions``

        Returns:
            str: Current calibration state: ``"uncalibrated"``,
                ``"ready_for_calibration"``, or ``"calibrated"``.
        """
        # Read current state
        current_state = get_reflection_config(self._db, domain, "calibration_state")
        if current_state == "calibrated":
            return "calibrated"
        if current_state == "ready_for_calibration":
            return "ready_for_calibration"

        # Read min_sessions config (default 30)
        min_sessions_str = get_reflection_config(self._db, domain, "min_sessions")
        min_sessions = (
            int(min_sessions_str) if min_sessions_str else _DEFAULT_MIN_SESSIONS
        )

        # Read review_threshold_days config (default 30), per governance R5
        review_days_str = get_reflection_config(
            self._db, domain, "review_threshold_days"
        )
        review_threshold_days = (
            int(review_days_str) if review_days_str else _DEFAULT_REVIEW_THRESHOLD_DAYS
        )

        # Time gate: at least review_threshold_days distinct calendar days
        time_row = self._db.execute(
            "SELECT COUNT(DISTINCT DATE(period_start)) FROM reflection_reports "
            "WHERE domain = ?",
            [domain],
        ).fetchone()
        time_gate = time_row[0] if time_row else 0

        # Evidence gate: at least min_sessions total reports
        evidence_row = self._db.execute(
            "SELECT COUNT(*) FROM reflection_reports WHERE domain = ?",
            [domain],
        ).fetchone()
        evidence_gate = evidence_row[0] if evidence_row else 0

        if time_gate >= review_threshold_days and evidence_gate >= min_sessions:
            # Auto-transition to ready_for_calibration
            set_reflection_config(
                self._db, domain, "calibration_state", "ready_for_calibration"
            )
            return "ready_for_calibration"

        return "uncalibrated"

    def persist_snapshot(
        self, execution_result: Any, domain: str
    ) -> None:
        """Extract strategy snapshot from execution result and persist to DB.

        Args:
            execution_result: ``ExecutionResult`` containing optional
                ``strategy_snapshot`` dict.
            domain: Market domain (e.g. ``"PM-5M"``).

        Raises:
            ValueError: If the snapshot dict is missing required keys
                (``transition_counts``).
        """
        snap = execution_result.strategy_snapshot
        if snap is None:
            return

        required = ["transition_counts"]
        missing = [k for k in required if k not in snap]
        if missing:
            raise ValueError(
                f"Snapshot missing required keys: {missing}"
            )

        from trady_ai.core.persistence import persist_strategy_snapshot

        persist_strategy_snapshot(
            db=self._db,
            domain=domain,
            strategy_name=snap.get("strategy_name", "unknown"),
            tick_number=snap.get("total_obs", 0),
            transition_counts=snap["transition_counts"],
            state_counts=snap.get("state_counts", []),
            warmup_ticks=snap.get("warmup_ticks", 0),
            threshold_pct=str(snap.get("threshold_pct", "0.001")),
            state_space_size=snap.get("state_space_size", 3),
            state_generator=snap.get("state_generator", "directional"),
            created_by="reflection_engine",
        )
