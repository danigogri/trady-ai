from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlite_utils

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.engine import ExecutionEngine, ExecutionResult
from trady_ai.core.models import MarketInput
from trady_ai.core.persistence import load_execution_log
from trady_ai.core.signal_strategy import SignalStrategy


def _reconstruct_market_input(row: dict[str, Any]) -> MarketInput:
    """Reconstruct a MarketInput from an execution_log row."""
    return MarketInput(
        timestamp=datetime.fromisoformat(row["timestamp"]),
        market_id=row["market_id"],
        price=Decimal(row["input_price"]),
        volume=Decimal(row["input_volume"]),
        source="replay",
    )


def replay(
    db: sqlite_utils.Database,
    strategy: SignalStrategy,
    config: RuntimeConfig,
) -> ExecutionResult:
    """Replay execution from DB log, reconstruct inputs, and re-run the pipeline.

    Loads the execution_log, rebuilds MarketInputs, creates a fresh
    ExecutionEngine, and re-executes the full pipeline. The replayed
    result should be identical to the original run.
    """
    log = load_execution_log(db)
    inputs = [_reconstruct_market_input(row) for row in log]
    engine = ExecutionEngine(config, db, dry_run=True)
    return engine.run(inputs, strategy)


def verify_replay(original: ExecutionResult, replayed: ExecutionResult) -> bool:
    """Compare two ExecutionResults field-by-field for determinism.

    Compares decisions, signals, and trades in order.
    Raises AssertionError with details on the first mismatch.
    Returns True if all fields match.
    """
    if len(original.decisions) != len(replayed.decisions):
        raise AssertionError(
            f"Decision count mismatch: {len(original.decisions)} vs {len(replayed.decisions)}"
        )
    for i, (a, b) in enumerate(zip(original.decisions, replayed.decisions)):
        if a.action != b.action:
            raise AssertionError(f"Decision {i} action mismatch: {a.action} vs {b.action}")
        if a.signal_id != b.signal_id:
            raise AssertionError(f"Decision {i} signal_id mismatch")
        if a.reason != b.reason:
            raise AssertionError(f"Decision {i} reason mismatch")

    if len(original.signals) != len(replayed.signals):
        raise AssertionError(
            f"Signal count mismatch: {len(original.signals)} vs {len(replayed.signals)}"
        )
    for i, (a, b) in enumerate(zip(original.signals, replayed.signals)):
        if a.id != b.id:
            raise AssertionError(f"Signal {i} id mismatch")
        if a.direction != b.direction:
            raise AssertionError(f"Signal {i} direction mismatch")
        if a.confidence != b.confidence:
            raise AssertionError(f"Signal {i} confidence mismatch")

    if len(original.trades) != len(replayed.trades):
        raise AssertionError(
            f"Trade count mismatch: {len(original.trades)} vs {len(replayed.trades)}"
        )
    for i, (a, b) in enumerate(zip(original.trades, replayed.trades)):
        if a.action != b.action:
            raise AssertionError(f"Trade {i} action mismatch")
        if a.id != b.id:
            raise AssertionError(f"Trade {i} id mismatch")

    return True
