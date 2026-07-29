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
from datetime import UTC, date, datetime
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

# Calendar day zero — fixed reference point for day computation (REQ-PT-019).
# Day 1 = 2026-07-28. Calendar day advances regardless of session execution.
DAY_ZERO = date(2026, 7, 28)

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
        duration: int = 60,
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
            duration: Capture window in seconds (default 60).

        Returns:
            ``SessionReport`` with stage timestamps, contract results, and
            aggregated counts.
        """
        day = self._compute_calendar_day()
        session_number = self._compute_session_number(domain)
        report = SessionReport(
            day=day,
            session_number=session_number,
            domain=domain,
            event_count=0,
            trade_count=0,
            reflection_report_id=None,
            market_ids=market_ids,
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
                    self._do_capture(market_ids, non_interactive, duration)
                except Exception:
                    logger.exception("capture_stage_failed")
                    self._record_stage(report, SessionState.ERROR)
                    report.contract_results = all_violations
                    return report
            else:
                logger.info("capture_skipped", reason="reconstruction")

            # Count events
            report.event_count = self._count_events()

            # ── Evidence guard ────────────────────────────────────────────────
            # Per spec: CAPTURING → ERROR when event_store has zero new events.
            # Only active when capture actually ran (not skipped by reconstruction).
            if SessionState.CAPTURING not in skip_stages and report.event_count == 0:
                logger.error(
                    "capture_produced_no_events",
                    day=day,
                    domain=domain,
                    market_ids=market_ids,
                )
                all_violations.append(
                    ContractViolation(
                        contract_name="EVIDENCE_COMPLETENESS",
                        severity="CRITICAL",
                        detail=(
                            f"Capture completed but produced zero events "
                            f"for domain={domain}, day={day}"
                        ),
                        timestamp=datetime.now(UTC).isoformat(),
                    )
                )
                self._record_stage(report, SessionState.ERROR)
                report.contract_results = all_violations
                return report

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
        # Compute last_processed_seq from execution_log for per-seq overlap check
        last_seq_row = self._db.execute(
            "SELECT COALESCE(MAX(tick_number), 0) FROM execution_log"
        ).fetchone()
        last_processed_seq = int(last_seq_row[0]) if last_seq_row else 0
        violations.extend(temporal_integrity(self._db, domain, last_processed_seq))
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

    def _do_capture(
        self, market_ids: list[str], non_interactive: bool, duration: int = 60
    ) -> None:
        """Run event capture for the given market IDs.

        In non-interactive mode, collects events for ``duration`` seconds.
        In interactive mode, waits for user to press Ctrl+C.

        Args:
            market_ids: List of market condition IDs to capture.
            non_interactive: When ``True``, uses timed capture.
            duration: Capture window in seconds (default 60).
        """
        from trady_ai.adapters.polymarket import EventCapture

        if self._adapter is None:
            logger.warning("capture_skipped_no_adapter")
            return

        # Translate condition_ids to token_ids (Polymarket WS expects asset_ids).
        # This fixes a bug where the WS was receiving condition_ids, which are
        # not the correct identifier for the CLOB WebSocket subscription.
        token_ids = self._resolve_token_ids(market_ids)
        if not token_ids:
            logger.warning("no_token_ids_resolved", condition_ids=market_ids)
        logger.info(
            "ws_subscription_tokens",
            condition_ids=market_ids,
            token_ids=token_ids,
        )

        capture = EventCapture(self._adapter, self._db)
        capture.start(token_ids)

        try:
            if non_interactive:
                # Timed capture — collect events for up to ``duration`` seconds
                timeout = duration
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
        """Per-clock reconstruction — no ``DATE(timestamp) = today``.

        Uses per-clock sequence tracking to detect interrupted sessions:

        - Trades exist but no matching reflection report → interrupted after
          EXECUTING → skip CAPTURING + EXECUTING, resume at REFLECTING.

        For normal sub-daily execution (all sessions complete), NO stages are
        skipped — every session runs capture, execute, and reflect independently.
        Per-clock tracking at the data level (``since_seq`` in execution engine)
        ensures event processing is idempotent.

        Returns:
            set[str]: Stage names to skip.
        """
        skip: set[str] = set()

        # Per-clock state queries
        max_seq_row = self._db.execute(
            "SELECT COALESCE(MAX(seq), 0) FROM event_store"
        ).fetchone()
        max_seq = int(max_seq_row[0]) if max_seq_row else 0

        last_processed_row = self._db.execute(
            "SELECT COALESCE(MAX(tick_number), 0) FROM execution_log"
        ).fetchone()
        last_processed_seq = int(last_processed_row[0]) if last_processed_row else 0

        # Latest reflection report creation timestamp
        report_row = self._db.execute(
            "SELECT MAX(created_at) FROM reflection_reports WHERE domain = ?",
            [domain],
        ).fetchone()
        last_report_ts = report_row[0] if report_row and report_row[0] else None

        # Latest trade timestamp
        trade_row = self._db.execute(
            "SELECT MAX(timestamp) FROM trades"
        ).fetchone()
        last_trade_ts = trade_row[0] if trade_row and trade_row[0] else None

        # ── Recovery detection (interrupted session) ────────────────────────
        # If execution_log has entries but no matching report exists for the
        # latest processed data, the previous session crashed after EXECUTING.
        if last_processed_seq > 0:
            if last_report_ts is None or (
                last_trade_ts is not None and last_trade_ts > last_report_ts
            ):
                skip.add("capturing")
                skip.add("executing")
                logger.info(
                    "reconstruction_interrupted_session",
                    last_trade_ts=last_trade_ts,
                    last_report_ts=last_report_ts,
                )

        logger.debug(
            "reconstruction_result",
            skip=list(skip),
            max_seq=max_seq,
            last_processed_seq=last_processed_seq,
            last_report_ts=last_report_ts,
            last_trade_ts=last_trade_ts,
        )
        return skip

    def _resolve_token_ids(self, condition_ids: list[str]) -> list[str]:
        """Translate Polymarket condition IDs to CLOB token IDs.

        For Polymarket: fetches market metadata and extracts token IDs.
        For other platforms (e.g., Binance): returns condition_ids directly
        — the market IDs are already valid subscription identifiers.

        Args:
            condition_ids: List of market identifiers.

        Returns:
            List of token/subscription IDs.
        """
        # Non-Polymarket adapters don't need token resolution
        if not hasattr(self._adapter, "get_market_data"):
            return list(condition_ids)

        token_ids: list[str] = []
        for cond_id in condition_ids:
            try:
                market = self._adapter.get_market_data(cond_id)
                for token in market.get("tokens", []):
                    tid = token.get("token_id", "")
                    if tid:
                        token_ids.append(tid)
            except Exception as e:  # noqa: BLE001 - log and skip, do not fail capture
                logger.warning(
                    "token_id_resolution_failed",
                    condition_id=cond_id,
                    error=str(e),
                )
        return token_ids

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

    def _compute_calendar_day(self) -> int:
        """Compute the current calendar day from DAY_ZERO (REQ-PT-019).

        Returns 1-based day number independent of session execution count.
        """
        delta = date.today() - DAY_ZERO
        return delta.days + 1

    def _compute_session_number(self, domain: str) -> int:
        """Compute 1-indexed session number for the domain today (REQ-PT-020).

        Counts existing reflection_reports for the same domain where
        DATE(created_at) = DATE('now'), then returns COUNT + 1.
        """
        row = self._db.execute(
            "SELECT COUNT(*) FROM reflection_reports "
            "WHERE domain = ? AND DATE(created_at) = DATE('now')",
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
