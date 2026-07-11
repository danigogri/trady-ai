import time

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
