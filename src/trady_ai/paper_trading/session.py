"""PaperTradingSession — stateless operational sequencer.

Coordinates the full session lifecycle:
  PRE_FLIGHT → CAPTURING → EXECUTING → REFLECTING → VERIFYING → BUNDLING → COMPLETE

Design follows ``ReflectionEngine.reflect()`` pattern: constructor takes
collaborators, one public method per cycle (``run_session``).

Operational Isolation Contract (REQ-PT-003):
  MUST NOT import ``strategies``, ``intelligence``, or ``governance``.
  Enforced via AST-level checks in ``contracts.validate_isolation_boundary()``.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import sqlite_utils
import structlog

from trady_ai.paper_trading.bundler import EvidenceBundler
from trady_ai.paper_trading.contracts import (
    deterministic_reproducibility,
    dry_run_enforced,
    evidence_completeness,
    no_real_funds,
    reflection_isolation,
    temporal_integrity,
    validate_isolation_boundary,
)
from trady_ai.paper_trading.models import ContractViolation, SessionReport, SessionState

logger = structlog.get_logger()

# Lazy import guard — EventCapture is imported inside the method to keep
# the module-level import boundary clean for AST checking.
_HAVE_EVENT_CAPTURE = False


class PaperTradingSession:
    """Stateless operational sequencer for paper trading sessions.

    Args:
        db: Database instance (sqlite_utils.Database).
        adapter: Optional PolymarketAdapter for event capture. When ``None``,
            capture is skipped (no market data to collect).
        execution_engine: Optional ``ExecutionEngine`` for running the strategy.
            When ``None``, a default engine is constructed internally.
        reflection_engine: Optional ``ReflectionEngine`` for post-execution
            analysis. When ``None``, a default engine is constructed internally.
    """

    # ── State machine sequence ───────────────────────────────────────────────
    _STAGES = [
        SessionState.PRE_FLIGHT,
        SessionState.CAPTURING,
        SessionState.EXECUTING,
        SessionState.REFLECTING,
        SessionState.VERIFYING,
        SessionState.BUNDLING,
    ]

    def __init__(
        self,
        db: sqlite_utils.Database,
        adapter: Any = None,
        execution_engine: Any = None,
        reflection_engine: Any = None,
    ) -> None:
        self._db = db
        self._adapter = adapter
        self._execution_engine = execution_engine
        self._reflection_engine = reflection_engine

    # ── Public API ───────────────────────────────────────────────────────────

    def run_session(
        self,
        scope: str,
        domain: str,
        market_ids: list[str],
        non_interactive: bool = False,
    ) -> SessionReport:
        """Execute full session lifecycle in a single invocation.

        Traverses all states sequentially. Exceptions are caught per-stage
        and result in ``ERROR`` state. Returns a ``SessionReport`` regardless
        of outcome.

        Args:
            scope: Time scope (e.g. ``"daily"``).
            domain: Market domain (e.g. ``"PM-5M"``).
            market_ids: List of market condition IDs to capture.
            non_interactive: When ``True``, uses timed capture instead of
                waiting for user input.

        Returns:
            ``SessionReport`` with stage timestamps, contract results, and
            aggregated counts.
        """
        day = self._compute_day(domain)
        report = SessionReport(
            day=day,
            domain=domain,
            event_count=0,
            trade_count=0,
            reflection_report_id=None,
        )

        # Collect ALL contract violations across stages
        all_violations: list[ContractViolation] = []

        try:
            # ── PRE_FLIGHT ───────────────────────────────────────────────────
            self._record_stage(report, SessionState.PRE_FLIGHT)
            pre_flight_ok = self._run_pre_flight(report, all_violations, domain)
            if not pre_flight_ok:
                self._record_stage(report, SessionState.ERROR)
                report.contract_results = all_violations
                return report

            # ── Determine which stages to skip via reconstruction ────────────
            skip_stages = self._reconstruct_stages(domain)

            # ── CAPTURING ────────────────────────────────────────────────────
            if SessionState.CAPTURING not in skip_stages:
                self._record_stage(report, SessionState.CAPTURING)
                try:
                    self._do_capture(market_ids, non_interactive)
                except Exception:
                    logger.exception("capture_stage_failed")
                    self._record_stage(report, SessionState.ERROR)
                    report.contract_results = all_violations
                    return report
            else:
                logger.info("capture_skipped", reason="reconstruction")

            # Count events
            report.event_count = self._count_events()

            # ── EXECUTING ────────────────────────────────────────────────────
            if SessionState.EXECUTING not in skip_stages:
                self._record_stage(report, SessionState.EXECUTING)
                try:
                    self._do_execute(scope, domain)
                except Exception:
                    logger.exception("execute_stage_failed")
                    self._record_stage(report, SessionState.ERROR)
                    report.contract_results = all_violations
                    return report
            else:
                logger.info("execute_skipped", reason="reconstruction")

            # Count trades
            report.trade_count = self._count_trades()

            # ── REFLECTING ───────────────────────────────────────────────────
            if SessionState.REFLECTING not in skip_stages:
                self._record_stage(report, SessionState.REFLECTING)
                try:
                    ref_report = self._do_reflect(scope, domain)
                    reflection_id = getattr(ref_report, "id", None)
                    cal_state = getattr(ref_report, "calibration_state", "not_ready")
                    if reflection_id is not None:
                        report.reflection_report_id = int(reflection_id)
                    report.calibration_state = cal_state
                except Exception:
                    logger.exception("reflect_stage_failed")
                    self._record_stage(report, SessionState.ERROR)
                    report.contract_results = all_violations
                    return report
            else:
                logger.info("reflect_skipped", reason="reconstruction")
                # Try to read existing reflection report id
                existing_id = self._read_existing_reflection_id(domain)
                if existing_id is not None:
                    report.reflection_report_id = existing_id

            # ── VERIFYING ────────────────────────────────────────────────────
            self._record_stage(report, SessionState.VERIFYING)
            verifying_ok = self._run_verifying(report, all_violations, domain)
            if not verifying_ok:
                self._record_stage(report, SessionState.ERROR)
                report.contract_results = all_violations
                return report

            # ── BUNDLING ─────────────────────────────────────────────────────
            self._record_stage(report, SessionState.BUNDLING)
            try:
                bundler = EvidenceBundler(self._db)
                bundler.bundle(report)
            except Exception:
                logger.exception("bundle_stage_failed")
                self._record_stage(report, SessionState.ERROR)
                report.contract_results = all_violations
                return report

        except Exception:
            logger.exception("session_unexpected_error")
            self._record_stage(report, SessionState.ERROR)
            report.contract_results = all_violations
            return report

        # ── COMPLETE ─────────────────────────────────────────────────────────
        report.contract_results = all_violations
        self._record_stage(report, SessionState.COMPLETE)
        logger.info(
            "session_complete",
            day=day,
            domain=domain,
            events=report.event_count,
            trades=report.trade_count,
        )
        return report

    # ── Stage implementations ────────────────────────────────────────────────

    def _run_pre_flight(
        self,
        report: SessionReport,
        violations: list[ContractViolation],
        domain: str,
    ) -> bool:
        """Evaluate gating contracts. Returns False on CRITICAL violations."""
        violations.extend(dry_run_enforced("dry_run"))
        violations.extend(no_real_funds(self._db))
        violations.extend(temporal_integrity(self._db, report.day, domain))
        violations.extend(validate_isolation_boundary())

        critical = [v for v in violations if v.severity == "CRITICAL"]
        if critical:
            logger.warning("pre_flight_critical_violations", count=len(critical))
            return False
        return True

    def _run_verifying(
        self,
        report: SessionReport,
        violations: list[ContractViolation],
        domain: str,
    ) -> bool:
        """Evaluate evidence contracts. Returns False on CRITICAL violations."""
        violations.extend(no_real_funds(self._db))
        violations.extend(evidence_completeness(self._db, domain, report.day))
        violations.extend(deterministic_reproducibility())
        violations.extend(reflection_isolation())

        critical = [v for v in violations if v.severity == "CRITICAL"]
        if critical:
            logger.warning("verifying_critical_violations", count=len(critical))
            return False
        return True

    def _do_capture(self, market_ids: list[str], non_interactive: bool) -> None:
        """Run event capture for the given market IDs.

        In non-interactive mode, collects events for a short duration.
        In interactive mode, waits for user to press Ctrl+C.
        """
        from trady_ai.adapters.polymarket import EventCapture

        if self._adapter is None:
            logger.warning("capture_skipped_no_adapter")
            return

        capture = EventCapture(self._adapter, self._db)
        capture.start(market_ids)

        try:
            if non_interactive:
                # Timed capture — collect events for up to 60 seconds
                timeout = 60
                start = time.monotonic()
                while capture.is_running and (time.monotonic() - start) < timeout:
                    time.sleep(1)
            else:
                # Interactive — wait for Ctrl+C
                print("Capture started. Press Ctrl+C to stop...")
                try:
                    while capture.is_running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
        finally:
            capture.stop()

    def _do_execute(self, scope: str, domain: str) -> None:
        """Run the execution engine on captured events."""
        from trady_ai.core.markov_strategy import MarkovStrategy

        engine = self._ensure_execution_engine()
        # Build a default strategy with conservative parameters
        strategy = MarkovStrategy(warmup_ticks=50, threshold_pct=0.001)
        engine.run_from_store(strategy, since_seq=0)

    def _do_reflect(self, scope: str, domain: str) -> Any:
        """Run the reflection engine for post-execution analysis."""
        engine = self._ensure_reflection_engine()
        return engine.reflect(scope=scope, domain=domain, mode="dry_run")

    # ── Reconstruction ──────────────────────────────────────────────────────

    def _reconstruct_stages(self, domain: str) -> set[str]:
        """Detect which stages are already complete from persisted evidence.

        Returns a set of state names to skip.
        """
        skip: set[str] = set()
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # CAPTURING: any events today?
        row = self._db.execute(
            "SELECT COUNT(*) FROM event_store WHERE DATE(timestamp) = ?",
            [today],
        ).fetchone()
        if row and row[0] and int(row[0]) > 0:
            skip.add("capturing")

        # EXECUTING: any trades today?
        row = self._db.execute(
            "SELECT COUNT(*) FROM trades WHERE DATE(timestamp) = ?",
            [today],
        ).fetchone()
        if row and row[0] and int(row[0]) > 0:
            skip.add("executing")

        # REFLECTING: any reflection report for this domain today?
        row = self._db.execute(
            "SELECT COUNT(*) FROM reflection_reports "
            "WHERE domain = ? AND DATE(created_at) = ?",
            [domain, today],
        ).fetchone()
        if row and row[0] and int(row[0]) > 0:
            skip.add("reflecting")

        logger.debug("reconstruction_result", skip=list(skip))
        return skip

    # ── Collaborator factories ───────────────────────────────────────────────

    def _ensure_execution_engine(self) -> Any:
        """Return execution engine, constructing a default if needed."""
        if self._execution_engine is not None:
            return self._execution_engine

        from trady_ai.config import get_settings
        from trady_ai.core.engine import ExecutionEngine

        settings = get_settings()
        config = settings.get_runtime_config()
        self._execution_engine = ExecutionEngine(config, self._db, dry_run=True)
        return self._execution_engine

    def _ensure_reflection_engine(self) -> Any:
        """Return reflection engine, constructing a default if needed."""
        if self._reflection_engine is not None:
            return self._reflection_engine

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer
        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer
        from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer
        from trady_ai.reflection.engine import ReflectionEngine
        from trady_ai.reflection.proposals.generator import ProposalGenerator

        self._reflection_engine = ReflectionEngine(
            db=self._db,
            outcome_analyzer=OutcomeAnalyzer(),
            signal_quality_analyzer=SignalQualityAnalyzer(),
            drift_analyzer=DriftAnalyzer(),
            proposal_generator=ProposalGenerator(),
        )
        return self._reflection_engine

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _compute_day(self, domain: str) -> int:
        """Compute the current session day (1-30) from existing reports."""
        row = self._db.execute(
            "SELECT COUNT(*) FROM reflection_reports WHERE domain = ?",
            [domain],
        ).fetchone()
        return (int(row[0]) if row and row[0] else 0) + 1

    def _count_events(self) -> int:
        """Count total events in event_store."""
        row = self._db.execute("SELECT COUNT(*) FROM event_store").fetchone()
        return int(row[0]) if row and row[0] else 0

    def _count_trades(self) -> int:
        """Count total trades (dry_run=1)."""
        row = self._db.execute(
            "SELECT COUNT(*) FROM trades WHERE dry_run = 1",
        ).fetchone()
        return int(row[0]) if row and row[0] else 0

    def _read_existing_reflection_id(self, domain: str) -> int | None:
        """Read the latest reflection report id for a domain."""
        row = self._db.execute(
            "SELECT MAX(id) FROM reflection_reports WHERE domain = ?",
            [domain],
        ).fetchone()
        return int(row[0]) if row and row[0] else None

    @staticmethod
    def _record_stage(report: SessionReport, state: SessionState) -> None:
        """Record the current timestamp for a state transition."""
        report.stage_timestamps[state.value.upper()] = datetime.now(UTC).isoformat()
