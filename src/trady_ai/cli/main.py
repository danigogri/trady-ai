import time
from typing import Any

import click

from trady_ai.config import get_settings


@click.group()
def cli() -> None:
    """Trady.AI - Deterministic financial intelligence infrastructure."""
    pass


@cli.command()
def status() -> None:
    """Show system configuration and event store statistics.

    Note: Capture state siempre 'stopped' en Fase 2 — EventCapture es efímero
    (vive dentro del comando capture, no es singleton). Fase 3+ con daemon/service
    trackeará real state.
    """
    settings = get_settings()
    click.echo("Trady.AI Status")
    click.echo(f"  Environment: {settings.environment}")
    click.echo(f"  Dry run: {settings.dry_run}")
    click.echo(f"  Log level: {settings.log_level}")
    click.echo(f"  DB path: {settings.db_path}")
    # IMPORTANTE: NO mostrar secrets_api_key
    from trady_ai.core.persistence import count_events, get_max_seq, init_event_store
    from trady_ai.db.database import get_db

    db = get_db(settings)
    init_event_store(db)
    event_count = count_events(db)
    max_seq = get_max_seq(db)
    click.echo(f"  Event store: {event_count} events (last seq: {max_seq})")
    click.echo(f"  Active markets: {settings.active_markets or '(none)'}")
    click.echo("  Capture: stopped")
    click.echo(f"  Execution mode: {settings.get_runtime_config().execution_mode}")


@cli.command()
@click.option("--input", "input_path", required=True, type=click.Path(exists=True), help="Path to CSV market data file")
@click.option("--threshold", default=0.001, type=float, help="Threshold pct for state classification")
@click.option("--warmup", default=50, type=int, help="Warmup ticks before signaling")
@click.option("--position-size", default="10.00", type=str, help="Fixed position size in USD")
@click.option("--transaction-cost", default=0.0, type=float, help="Transaction cost percentage")
@click.option("--stop-loss", default=0.05, type=float, help="Stop loss percentage (0.05 = 5%%)")
def backtest(
    input_path: str,
    threshold: float,
    warmup: int,
    position_size: str,
    transaction_cost: float,
    stop_loss: float,
) -> None:
    """Run backtest on CSV market data."""
    from decimal import Decimal
    from pathlib import Path

    from trady_ai.config import get_settings
    from trady_ai.config.runtime_config import RuntimeConfig
    from trady_ai.core.engine import ExecutionEngine
    from trady_ai.core.ingestion import read_csv
    from trady_ai.core.markov_strategy import MarkovStrategy
    from trady_ai.core.replay import replay, verify_replay
    from trady_ai.db.database import get_db

    settings = get_settings()
    config = RuntimeConfig(
        threshold_pct=threshold,
        warmup_ticks=warmup,
        position_size=Decimal(position_size),
        transaction_cost_pct=transaction_cost,
        stop_loss_pct=stop_loss,
    )
    db = get_db(settings)
    inputs = read_csv(Path(input_path))
    strategy = MarkovStrategy(config.warmup_ticks, config.threshold_pct)
    engine = ExecutionEngine(config, db, dry_run=True)
    result = engine.run(inputs, strategy)

    click.echo("")
    click.echo("Backtest Results")
    click.echo(f"  Total signals: {result.summary_stats['total_signals']}")
    click.echo(f"  Total trades: {result.summary_stats['total_trades']}")
    click.echo(f"  Win rate: {result.summary_stats['win_rate']:.2%}")
    click.echo(f"  Total PnL: ${result.summary_stats['total_pnl']:.2f}")
    click.echo(f"  Max drawdown: ${result.summary_stats['max_drawdown']:.2f}")

    # Verify replay with a fresh strategy (engine.run mutates strategy state)
    replay_strategy = MarkovStrategy(config.warmup_ticks, config.threshold_pct)
    replay_result = replay(db, replay_strategy, config)
    verify_replay(result, replay_result)
    click.echo("")
    click.echo("  Replay verification: PASS")


@cli.command()
@click.option("--market", required=True, help="Market ID or symbol")
def analyze(market: str) -> None:
    """Analyze signals for a specific market."""
    from trady_ai.config import get_settings
    from trady_ai.core.persistence import init_core_tables
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)
    init_core_tables(db)

    signals_table = db["signals"]
    recent = list(
        signals_table.rows_where(
            "market_id = ?",
            [market],
            order_by="timestamp DESC",
            limit=5,
        )
    )

    if not recent:
        click.echo(f"No signals found for market: {market}")
        return

    click.echo(f"Recent signals for {market}:")
    for s in recent:
        click.echo(
            f"  {s['timestamp']}: {s['direction']} (confidence={s['confidence']:.2f}, strategy={s['strategy_name']})"
        )


@cli.command()
@click.option("--market", required=True, help="Market ID to run engine on")
@click.option("--since-seq", default=0, type=int, help="Start from event seq (0 = all)")
def run(market: str, since_seq: int) -> None:
    """Run the deterministic engine on captured market data."""
    from trady_ai.config import get_settings
    from trady_ai.core.engine import ExecutionEngine
    from trady_ai.core.markov_strategy import MarkovStrategy
    from trady_ai.core.persistence import count_events
    from trady_ai.db.database import get_db

    settings = get_settings()
    config = settings.get_runtime_config()
    db = get_db(settings)

    from trady_ai.security.polymarket import validate_execution_secrets

    validate_execution_secrets(settings, config.execution_mode)

    event_count = count_events(db)
    if event_count == 0:
        click.echo("No events in event_store. Run 'trady-ai capture' first.")
        return

    strategy = MarkovStrategy(config.warmup_ticks, config.threshold_pct)
    engine = ExecutionEngine(config, db, dry_run=(config.execution_mode == "dry_run"))

    click.echo(f"Running engine on {event_count} events (dry_run={config.execution_mode})...")
    result = engine.run_from_store(strategy, since_seq=since_seq)

    click.echo("\nExecution Results:")
    click.echo(f"  Total signals: {result.summary_stats['total_signals']}")
    click.echo(f"  Total trades: {result.summary_stats['total_trades']}")
    if result.summary_stats.get("closed_positions", 0) > 0:
        click.echo(f"  Win rate: {result.summary_stats['win_rate']:.2%}")
    else:
        click.echo("  Win rate: N/A (no closed positions)")
    click.echo(f"  Total PnL: ${result.summary_stats['total_pnl']:.2f}")
    click.echo(f"  Max drawdown: ${result.summary_stats['max_drawdown']:.2f}")
    click.echo(f"  Execution mode: {config.execution_mode}")


@cli.command()
@click.option("--markets", default="", help="Comma-separated market IDs (default: from settings)")
@click.option("--reset", is_flag=True, help="Reset event_store before capture (dev only)")
def capture(markets: str, reset: bool) -> None:
    """Start WebSocket market data capture."""
    from trady_ai.adapters.polymarket import EventCapture, PolymarketAdapter
    from trady_ai.config import get_settings
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)

    from trady_ai.security.polymarket import validate_execution_secrets

    validate_execution_secrets(settings, settings.get_runtime_config().execution_mode)

    adapter = PolymarketAdapter(
        rest_url=settings.polymarket_rest_url,
        ws_url=settings.polymarket_ws_url,
        api_key=settings.polymarket_api_key,
    )
    capture_obj = EventCapture(adapter, db)

    market_ids = [m.strip() for m in markets.split(",") if m.strip()] if markets else settings.get_active_market_ids()
    if not market_ids:
        click.echo("No markets specified. Use --markets or configure active_markets in settings.")
        return

    if reset:
        capture_obj.reset()
        click.echo("Event store reset.")

    capture_obj.start(market_ids)
    click.echo(f"Capture started for {len(market_ids)} market(s). Press Ctrl+C to stop.")
    click.echo("Run 'trady-ai status' to check capture state.")

    try:
        while capture_obj.is_running:
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        capture_obj.stop()
        click.echo("Capture stopped.")


# ── Calibration Commands ──────────────────────────────────────────────────────


@cli.group()
def calibrate() -> None:
    """Calibration: review evidence and adopt state spaces."""
    pass


@calibrate.command()
@click.option("--domain", required=True, help="Market domain (e.g. PM-5M)")
@click.option("--strategy", "strategy_name", default="markov_persistence",
              help="Strategy name (default: markov_persistence)")
def review(domain: str, strategy_name: str) -> None:
    """Review calibration evidence for a domain/strategy.

    Displays AIC, BIC, Markov χ², state persistence, and conditional entropy.
    """
    from trady_ai.config import get_settings
    from trady_ai.core.persistence import init_core_tables
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)
    init_core_tables(db)

    from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

    analyzer = CalibrationAnalyzer()
    report = analyzer.analyze(db, domain, strategy_name=strategy_name)

    click.echo("Calibration Evidence Report")
    click.echo(f"  Domain: {domain}")
    click.echo(f"  Strategy: {strategy_name}")
    click.echo(f"  States (|S|): {report.num_states}")
    click.echo(f"  Observations: {report.num_observations}")

    if report.num_states == 0:
        click.echo("  (no data available)")
        raise SystemExit(0)

    click.echo("")
    click.echo("  ── Information Criteria ──")
    click.echo(f"  AIC: {report.aic:.4f}")
    click.echo(f"  BIC: {report.bic:.4f}")

    click.echo("")
    click.echo("  ── Markov χ² Test (first-order) ──")
    mt = report.markov_test
    click.echo(f"  χ² statistic: {mt.get('statistic', 'N/A')}")
    click.echo(f"  p-value: {mt.get('p_value', 'N/A')}")
    click.echo(f"  df: {mt.get('df', 'N/A')}")
    click.echo(f"  Reject H0 (not first-order): {mt.get('reject_null', 'N/A')}")

    click.echo("")
    click.echo("  ── State Persistence (mean residence time) ──")
    for state_idx, mean_time in report.state_persistence.items():
        click.echo(f"  State {state_idx}: {mean_time} ticks")

    click.echo("")
    click.echo("  ── Entropy ──")
    click.echo(f"  Conditional entropy H(X_n+1|X_n): {report.conditional_entropy:.6f} bits")
    click.echo("")
    click.echo(f"  Computed: {report.computed_at}")

    raise SystemExit(0)


@calibrate.command()
@click.option("--domain", required=True, help="Market domain (e.g. PM-5M)")
@click.option("--states", type=int, required=True, help="Number of states (|S|)")
@click.option("--generator", required=True, help="State generator name")
@click.option("--strategy", "strategy_name", default="markov_persistence",
              help="Strategy name (default: markov_persistence)")
@click.option("--confirm", is_flag=True, help="Confirm adoption (required to persist)")
@click.option("--reason", default="", help="Human-supplied reason for adoption")
def adopt(
    domain: str,
    states: int,
    generator: str,
    strategy_name: str,
    confirm: bool,
    reason: str,
) -> None:
    """Adopt a new state space configuration.

    Validates |S| >= 2 and generator exists. Requires --confirm to persist.
    Without --confirm, displays summary and exits with code 1.
    """
    from trady_ai.config import get_settings
    from trady_ai.core.persistence import init_core_tables
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)
    init_core_tables(db)

    # Validate states >= 2
    if states < 2:
        click.echo(f"Error: Number of states must be >= 2, got {states}", err=True)
        raise SystemExit(1)

    # Validate generator exists
    from trady_ai.strategies.markov import get_generator

    try:
        get_generator(generator, state_space_size=states)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    # Generate evidence report
    from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer
    from trady_ai.reflection.calibration.persistence import (
        init_calibration_tables,
        save_adoption,
    )

    analyzer = CalibrationAnalyzer()
    evidence = analyzer.analyze(db, domain, strategy_name=strategy_name)

    # Display summary
    click.echo("Adoption Summary")
    click.echo(f"  Domain: {domain}")
    click.echo(f"  Strategy: {strategy_name}")
    click.echo(f"  States: {states}")
    click.echo(f"  Generator: {generator}")
    click.echo(f"  Current AIC: {evidence.aic:.4f}")
    click.echo(f"  Current BIC: {evidence.bic:.4f}")
    click.echo("")

    if not confirm:
        click.echo("Use --confirm to persist this adoption. Exiting without changes.", err=True)
        raise SystemExit(1)

    # Persist adoption with provenance
    import os
    import socket

    operator = os.environ.get("USER", "unknown")
    hostname = socket.gethostname()
    operator_str = f"{operator}@{hostname}"

    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    evidence_ref = f"aic={evidence.aic:.2f},bic={evidence.bic:.2f}"

    from trady_ai.reflection.calibration.models import AdoptedStateSpace

    adoption = AdoptedStateSpace(
        domain=domain,
        strategy_name=strategy_name,
        states=states,
        generator=generator,
        evidence_report_ref=evidence_ref,
        operator=operator_str,
        adopted_at=now,
        reason=reason,
    )
    init_calibration_tables(db)
    adoption_id = save_adoption(db, adoption)

    # Write bundle
    from trady_ai.paper_trading.bundler import EvidenceBundler

    bundler = EvidenceBundler(db)
    bundle_path = bundler.calibration_bundle(evidence, adoption)

    click.echo(f"Adoption recorded (ID: {adoption_id})")
    click.echo(f"Bundle: {bundle_path}")
    click.echo(f"  Evidence ref: {evidence_ref}")
    click.echo(f"  Operator: {operator_str}")

    # Store in reflection_config
    from trady_ai.reflection.persistence import set_reflection_config

    set_reflection_config(db, domain, "calibration_state", "calibrated")
    set_reflection_config(db, domain, f"adopted_states_{strategy_name}", str(states))
    set_reflection_config(db, domain, f"adopted_generator_{strategy_name}", generator)

    db.conn.commit()
    raise SystemExit(0)


# ── Paper Trading Commands ─────────────────────────────────────────────────────


@cli.group()
def paper_trade() -> None:
    """Paper Trading operational commands."""
    pass


_VALID_DOMAIN_SET = {"FOOTBALL-WINNER", "CRYPTO-BINARY", "BINANCE-SPOT"}


@paper_trade.command()
@click.option("--scope", default="daily", help="Time scope (default: daily)")
@click.option("--domain", required=True, help="Market domain (e.g. PM-5M)")
@click.option("--markets", multiple=True, help="Market condition IDs or symbols")
@click.option("--non-interactive", is_flag=True, default=False, help="Timed capture without prompts")
@click.option("--duration", default=60, type=int, help="Capture window in seconds (default: 60)")
def session(scope: str, domain: str, markets: tuple[str, ...], non_interactive: bool, duration: int) -> None:
    """Run a paper trading session."""
    from trady_ai.config import get_settings
    from trady_ai.db.database import get_db

    # Validate domain early — fail fast on unknown domains
    if domain not in _VALID_DOMAIN_SET:
        valid_list = ", ".join(sorted(_VALID_DOMAIN_SET))
        click.echo(f"Unknown domain: {domain}. Valid domains: {valid_list}", err=True)
        raise SystemExit(1)

    settings = get_settings()
    db = get_db(settings)

    from trady_ai.adapters.polymarket import PolymarketAdapter
    from trady_ai.paper_trading.session import PaperTradingSession

    adapter: Any
    if domain == "BINANCE-SPOT":
        from trady_ai.adapters.binance import BinanceAdapter

        symbols = list(markets) if markets else settings.get_active_symbols()
        if not symbols:
            click.echo(
                "No symbols configured. Set TRADY_AI_ACTIVE_SYMBOLS in .env or use --markets.",
                err=True,
            )
            raise SystemExit(1)

        adapter = BinanceAdapter(
            ws_url=settings.binance_ws_url,
            rest_url=settings.binance_rest_url,
        )
        market_ids = [s.lower() for s in symbols]
    else:
        market_ids = list(markets) if markets else settings.get_active_market_ids()
        if not market_ids:
            click.echo("No markets specified. Use --markets or configure active_markets in settings.")
            return

        adapter = PolymarketAdapter(
            rest_url=settings.polymarket_rest_url,
            ws_url=settings.polymarket_ws_url,
            api_key=settings.polymarket_api_key,
        )
    paper_session = PaperTradingSession(db, adapter=adapter)
    report = paper_session.run_session(
        scope=scope,
        domain=domain,
        market_ids=market_ids,
        non_interactive=non_interactive,
        duration=duration,
    )

    has_error = "ERROR" in report.stage_timestamps

    click.echo(f"Paper Trading Session — Day {report.day}, Domain: {report.domain}")
    click.echo(f"  State: {'ERROR' if has_error else 'COMPLETE'}")
    click.echo(f"  Events: {report.event_count}, Trades: {report.trade_count}")
    click.echo(f"  Market IDs: {', '.join(report.market_ids) if report.market_ids else '(none)'}")
    click.echo(f"  Reflection report: #{report.reflection_report_id or 'N/A'}")
    click.echo(f"  Calibration: {report.calibration_state}")

    if has_error:
        critical = [v for v in report.contract_results if v.severity == "CRITICAL"]
        if critical:
            click.echo("  Contract violations:")
            for v in critical:
                click.echo(f"    - [{v.severity}] {v.contract_name}: {v.detail}")
        raise SystemExit(1)

    raise SystemExit(0)


@paper_trade.command(name="status")
def paper_trade_status() -> None:
    """Show paper trading progress (day N/30)."""
    from trady_ai.config import get_settings
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)

    from trady_ai.core.persistence import init_core_tables

    init_core_tables(db)

    row = db.execute(
        "SELECT COUNT(DISTINCT DATE(created_at)) FROM reflection_reports"
    ).fetchone()
    report_days = int(row[0]) if row and row[0] else 0

    click.echo(f"Paper Trading Progress: Day {report_days}/30")


@paper_trade.command()
@click.option("--day", type=int, required=True, help="Session day to bundle")
@click.option("--domain", default="PM-5M", help="Market domain")
def bundle(day: int, domain: str) -> None:
    """Regenerate evidence bundle for a past day."""
    from trady_ai.config import get_settings
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)

    from trady_ai.paper_trading.bundler import EvidenceBundler

    bundler_obj = EvidenceBundler(db)
    try:
        bundle_path = bundler_obj.regenerate_bundle(day, domain)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    manifest_file = bundle_path / "manifest.json"
    click.echo(f"Bundle generated: {bundle_path}")
    if manifest_file.exists():
        import json

        manifest = json.loads(manifest_file.read_text())
        click.echo(f"  Artifacts: {', '.join(manifest.get('artifact_checksums', {}).keys())}")
    raise SystemExit(0)


# ── Reflection Analysis Commands ──────────────────────────────────────────────


@cli.group()
def reflect() -> None:
    """Post-execution analysis: evaluate outcomes, detect drift, generate proposals."""
    pass


@reflect.command(name="analyze")
@click.option("--scope", type=click.Choice(["session", "daily", "weekly"]), default="session",
              help="Analysis window scope")
@click.option("--domain", default="PM-5M", help="Trading domain to analyze")
@click.option("--mode", type=click.Choice(["dry_run"]), default="dry_run",
              help="Execution mode (only dry_run supported in Phase 4)")
@click.option("--baseline-tick", type=int, default=None,
              help="Baseline snapshot tick for drift comparison (default: second-to-latest)")
@click.option("--comparison-tick", type=int, default=None,
              help="Comparison snapshot tick for drift comparison (default: latest)")
def cmd_analyze(scope: str, domain: str, mode: str,
                baseline_tick: int | None, comparison_tick: int | None) -> None:
    """Run reflection analysis: outcomes, signal quality, drift detection."""
    from trady_ai.config import get_settings
    from trady_ai.core.persistence import init_core_tables
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)
    init_core_tables(db)
    engine = _build_reflection_engine(db)
    report = engine.reflect(
        scope=scope,
        domain=domain,
        mode=mode,
        baseline_tick=baseline_tick,
        comparison_tick=comparison_tick,
    )
    click.echo(_format_analysis_output(report))


@reflect.command()
@click.option("--domain", default="PM-5M", help="Trading domain")
def report(domain: str) -> None:
    """Show the most recent reflection report for a domain."""
    import json

    from trady_ai.config import get_settings
    from trady_ai.core.persistence import init_core_tables
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)
    init_core_tables(db)

    rows = list(db.query(
        "SELECT * FROM reflection_reports WHERE domain = ? ORDER BY id DESC LIMIT 1",
        [domain],
    ))
    if not rows:
        click.echo(f"No reflection reports found for domain: {domain}")
        return

    row = rows[0]
    click.echo(f"Reflection Report #{row['id']}")
    click.echo(f"  Scope: {row['scope']}")
    click.echo(f"  Domain: {row['domain']}")
    click.echo(f"  Mode: {row['mode']}")
    click.echo(f"  Period: {row['period_start']} \u2014 {row['period_end']}")
    click.echo(f"  Created: {row['created_at']}")

    # Parse and display report summary
    try:
        data = json.loads(row["report_data"])
    except (json.JSONDecodeError, TypeError):
        click.echo("  (report data unavailable)")
        return

    if "outcome_summary" in data:
        os = data["outcome_summary"]
        click.echo("")
        click.echo("  Outcome Summary:")
        click.echo(f"    Total trades: {os.get('total_trades', 'N/A')}")
        click.echo(f"    Win rate: {os.get('win_rate', 0.0):.1%}")
        click.echo(f"    Total PnL: ${os.get('total_pnl', '0.00')}")

    if "signal_quality" in data:
        sq = data["signal_quality"]
        click.echo("")
        click.echo("  Signal Quality:")
        click.echo(f"    Total signals: {sq.get('total_signals', 'N/A')}")
        click.echo(f"    Signal accuracy: {sq.get('signal_accuracy', 0.0):.1%}")

    if "drift_events" in data and data["drift_events"]:
        click.echo("")
        click.echo("  Drift Alerts:")
        for ev in data["drift_events"]:
            click.echo(
                f"    - {ev['metric']}: {ev['deviation_pct']:.1f}% deviation "
                f"(threshold: {ev['threshold']:.0%})"
            )
    else:
        click.echo("")
        click.echo("  Drift Alerts: none")

    if "proposals" in data and data["proposals"]:
        click.echo("")
        click.echo("  Proposals:")
        for prop in data["proposals"]:
            click.echo(
                f"    - {prop['parameter_name']}: {prop['current_value']} \u2192 "
                f"{prop['proposed_value']} ({prop['status']})"
            )
    else:
        click.echo("")
        click.echo("  Proposals: none")


@reflect.command()
@click.option("--domain", default="PM-5M", help="Trading domain")
def propose(domain: str) -> None:
    """Generate bounded parameter proposals from latest drift analysis."""
    from trady_ai.config import get_settings
    from trady_ai.core.persistence import init_core_tables
    from trady_ai.db.database import get_db

    settings = get_settings()
    db = get_db(settings)
    init_core_tables(db)
    engine = _build_reflection_engine(db)

    # Default current parameter values for proposal generation
    current_params: dict[str, float] = {
        "warmup_ticks": 50.0,
        "threshold_pct": 0.001,
    }

    # Run reflect with daily scope to generate drift-based proposals
    report = engine.reflect(
        scope="daily",
        domain=domain,
        mode="dry_run",
        current_params=current_params,
    )

    if not report.proposals:
        click.echo(f"No proposals generated for domain: {domain}")
        return

    click.echo(f"Proposals for {domain}:")
    for p in report.proposals:
        click.echo(f"  {p.parameter_name}: {p.current_value} \u2192 {p.proposed_value}")
        click.echo(f"    Range: [{p.range_min}, {p.range_max}]")
        click.echo(f"    Status: {p.status}")
        click.echo(f"    Justification: {p.justification}")
        click.echo("")


# ── Reflection Helpers ────────────────────────────────────────────────────────


def _build_reflection_engine(db: object) -> Any:
    """Factory: build ReflectionEngine with all dependencies wired."""
    from trady_ai.reflection.analyzers.drift import DriftAnalyzer
    from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer
    from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer
    from trady_ai.reflection.engine import ReflectionEngine
    from trady_ai.reflection.proposals.generator import ProposalGenerator

    # db is sqlite_utils.Database; we keep param as object to avoid top-level
    # import of sqlite_utils in this CLI module
    assert hasattr(db, "execute"), "db must be a sqlite_utils.Database"

    return ReflectionEngine(
        db=db,  # type: ignore[arg-type]
        outcome_analyzer=OutcomeAnalyzer(),
        signal_quality_analyzer=SignalQualityAnalyzer(),
        drift_analyzer=DriftAnalyzer(),
        proposal_generator=ProposalGenerator(),
    )


def _format_analysis_output(report: object) -> str:
    """Format a ReflectionReport for CLI display."""

    from trady_ai.reflection.models import ReflectionReport

    assert isinstance(report, ReflectionReport)
    r: ReflectionReport = report

    lines: list[str] = []
    lines.append("Reflection Analysis Report")
    lines.append(f"  Scope: {r.scope}")
    lines.append(f"  Domain: {r.domain}")
    lines.append(f"  Mode: {r.mode}")
    lines.append(
        f"  Period: {r.period_start.isoformat()} \u2014 {r.period_end.isoformat()}"
    )
    lines.append(f"  Calibration: {r.calibration_state}")

    if r.outcome_summary is not None:
        os = r.outcome_summary
        lines.append("")
        lines.append("  Outcome Summary:")
        lines.append(f"    Total trades: {os.total_trades}")
        lines.append(f"    Win rate: {os.win_rate:.1%}")
        lines.append(f"    Total PnL: ${os.total_pnl}")
        lines.append(f"    Avg PnL/trade: ${os.avg_pnl_per_trade}")
        lines.append(f"    Max drawdown: ${os.max_drawdown}")
    else:
        lines.append("")
        lines.append("  Outcome Summary: (none)")

    if r.signal_quality is not None:
        sq = r.signal_quality
        lines.append("")
        lines.append("  Signal Quality:")
        lines.append(f"    Total signals: {sq.total_signals}")
        lines.append(f"    Signal accuracy: {sq.signal_accuracy:.1%}")
        lines.append(f"    Avg confidence: {sq.avg_confidence:.2f}")
    else:
        lines.append("")
        lines.append("  Signal Quality: (none)")

    if r.drift_events:
        lines.append("")
        lines.append("  Drift Alerts:")
        for ev in r.drift_events:
            lines.append(
                f"    - {ev.metric}: {ev.deviation_pct:.1f}% deviation "
                f"(threshold: {ev.threshold:.0%})"
            )
    else:
        lines.append("")
        lines.append("  Drift Alerts: none")

    if r.proposals:
        lines.append("")
        lines.append("  Proposals:")
        for p in r.proposals:
            lines.append(
                f"    - {p.parameter_name}: {p.current_value} \u2192 "
                f"{p.proposed_value} ({p.status})"
            )
    else:
        lines.append("")
        lines.append("  Proposals: none")

    return "\n".join(lines)
