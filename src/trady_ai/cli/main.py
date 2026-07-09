import click

from trady_ai.config import get_settings


@click.group()
def cli() -> None:
    """Trady.AI - Deterministic financial intelligence infrastructure."""
    pass


@cli.command()
def status() -> None:
    """Show system configuration."""
    settings = get_settings()
    click.echo("Trady.AI Status")
    click.echo(f"  Environment: {settings.environment}")
    click.echo(f"  Dry run: {settings.dry_run}")
    click.echo(f"  Log level: {settings.log_level}")
    click.echo(f"  DB path: {settings.db_path}")
    # IMPORTANTE: NO mostrar secrets_api_key


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
@click.option("--market", required=True, help="Market ID or symbol")
def run(market: str) -> None:
    """Run execution for a market (simulated in Phase 1)."""
    from trady_ai.config import get_settings

    settings = get_settings()
    click.echo(f"Simulated execution (dry_run=True) for market: {market}")
    click.echo(f"Environment: {settings.environment}")
    click.echo("Live execution will be available in Phase 2.")
