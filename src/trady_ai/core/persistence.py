import json
from typing import Any

import sqlite_utils

from trady_ai.core.models import ExecutionDecision, MarketInput, MarketState, Position, Signal, Trade


def init_core_tables(db: sqlite_utils.Database) -> None:
    """Create the 5 core tables if they don't exist. Idempotent."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS market_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            price TEXT NOT NULL,
            volume TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('UP', 'DOWN', 'NEUTRAL')),
            previous_state TEXT CHECK(previous_state IN ('UP', 'DOWN', 'NEUTRAL', NULL)),
            source TEXT DEFAULT 'state_tracker'
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS signals (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            market_id TEXT NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT', 'NEUTRAL')),
            confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
            strategy_name TEXT NOT NULL,
            metadata TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            market_id TEXT NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
            entry_price TEXT NOT NULL,
            current_price TEXT NOT NULL,
            size TEXT NOT NULL,
            pnl TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'CLOSED')),
            signal_id TEXT NOT NULL REFERENCES signals(id)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL REFERENCES signals(id),
            position_id TEXT NOT NULL REFERENCES positions(id),
            action TEXT NOT NULL CHECK(action IN ('OPEN', 'CLOSE')),
            price TEXT NOT NULL,
            size TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            dry_run INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tick_number INTEGER NOT NULL,
            market_id TEXT NOT NULL,
            input_price TEXT NOT NULL,
            input_volume TEXT NOT NULL,
            state TEXT NOT NULL,
            signal_id TEXT REFERENCES signals(id),
            decision_action TEXT NOT NULL,
            decision_reason TEXT,
            trade_id TEXT REFERENCES trades(id),
            timestamp TEXT NOT NULL
        )
        """
    )


def persist_market_state(db: sqlite_utils.Database, state: MarketState) -> None:
    """Insert a MarketState record. Prices stored as TEXT (Decimal string)."""
    db["market_states"].insert(
        {
            "market_id": state.market_id,
            "timestamp": state.timestamp.isoformat(),
            "price": str(state.price),
            "volume": str(state.volume),
            "state": state.state,
            "previous_state": state.previous_state,
            "source": state.source,
        }
    )


def persist_signal(db: sqlite_utils.Database, signal: Signal) -> None:
    """Insert or replace a Signal. Metadata serialized as JSON."""
    db["signals"].insert(
        {
            "id": str(signal.id),
            "timestamp": signal.timestamp.isoformat(),
            "market_id": signal.market_id,
            "direction": signal.direction,
            "confidence": signal.confidence,
            "strategy_name": signal.strategy_name,
            "metadata": json.dumps(signal.metadata),
        },
        pk="id",
        replace=True,
    )


def persist_position(db: sqlite_utils.Database, position: Position) -> None:
    """Insert or replace a Position (upsert by id)."""
    db["positions"].insert(
        {
            "id": str(position.id),
            "market_id": position.market_id,
            "direction": position.direction,
            "entry_price": str(position.entry_price),
            "current_price": str(position.current_price),
            "size": str(position.size),
            "pnl": str(position.pnl) if position.pnl is not None else None,
            "status": position.status,
            "signal_id": str(position.signal_id),
        },
        pk="id",
        replace=True,
    )


def persist_trade(db: sqlite_utils.Database, trade: Trade) -> None:
    """Insert a Trade record. dry_run stored as INTEGER (SQLite boolean)."""
    db["trades"].insert(
        {
            "id": str(trade.id),
            "signal_id": str(trade.signal_id),
            "position_id": str(trade.position_id),
            "action": trade.action,
            "price": str(trade.price),
            "size": str(trade.size),
            "timestamp": trade.timestamp.isoformat(),
            "dry_run": 1 if trade.dry_run else 0,
        },
        pk="id",
        replace=True,
    )


def persist_execution_log(
    db: sqlite_utils.Database,
    tick_number: int,
    market_input: MarketInput,
    state: MarketState,
    signal: Signal,
    decision: ExecutionDecision,
    trade: Trade | None,
) -> None:
    """Insert an execution log entry for one tick."""
    db["execution_log"].insert(
        {
            "tick_number": tick_number,
            "market_id": market_input.market_id,
            "input_price": str(market_input.price),
            "input_volume": str(market_input.volume),
            "state": state.state,
            "signal_id": str(signal.id),
            "decision_action": decision.action,
            "decision_reason": decision.reason,
            "trade_id": str(trade.id) if trade is not None else None,
            "timestamp": market_input.timestamp.isoformat(),
        }
    )


def load_execution_log(db: sqlite_utils.Database) -> list[dict[str, Any]]:
    """Load the complete execution log ordered by tick_number."""
    return list(db["execution_log"].rows_where(order_by="tick_number"))
