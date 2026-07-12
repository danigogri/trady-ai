import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import sqlite_utils

from trady_ai.core.models import ExecutionDecision, MarketInput, MarketState, Position, Signal, Trade


def init_core_tables(db: sqlite_utils.Database) -> None:
    """Create core tables if they don't exist. Idempotent."""
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
    db.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
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
    init_event_store(db)
    init_strategy_tables(db)
    init_reflection_tables(db)


def persist_market_state(db: sqlite_utils.Database, state: MarketState) -> None:
    """Insert a MarketState record. Prices stored as TEXT (Decimal string)."""
    db["market_states"].insert(  # type: ignore[union-attr]
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
    db["signals"].insert(  # type: ignore[union-attr]
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
    db["positions"].insert(  # type: ignore[union-attr]
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
    db["trades"].insert(  # type: ignore[union-attr]
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
    db["execution_log"].insert(  # type: ignore[union-attr]
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


# ── Time-Bounded Query Helpers ────────────────────────────────────────────────


def query_trades_by_time_range(
    db: sqlite_utils.Database, start: str, end: str
) -> list[dict[str, Any]]:
    """Return trades within time range, ordered by timestamp ASC.

    Args:
        db: Database instance.
        start: ISO-8601 start timestamp (inclusive).
        end: ISO-8601 end timestamp (inclusive).

    Returns:
        List of trade row dicts matching the time range.
    """
    return list(
        db["trades"].rows_where(
            "timestamp >= ? AND timestamp <= ?",
            [start, end],
            order_by="timestamp ASC",
        )
    )


def query_signals_by_time_range(
    db: sqlite_utils.Database, start: str, end: str
) -> list[dict[str, Any]]:
    """Return signals within time range, ordered by timestamp ASC.

    Args:
        db: Database instance.
        start: ISO-8601 start timestamp (inclusive).
        end: ISO-8601 end timestamp (inclusive).

    Returns:
        List of signal row dicts matching the time range.
    """
    return list(
        db["signals"].rows_where(
            "timestamp >= ? AND timestamp <= ?",
            [start, end],
            order_by="timestamp ASC",
        )
    )


# ── Event Store ──────────────────────────────────────────────────────────────


def init_event_store(db: sqlite_utils.Database) -> None:
    """Create event_store table if not exists. Idempotent.

    Called from init_core_tables() or independently.
    """
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS event_store (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            market_id TEXT NOT NULL,
            price TEXT NOT NULL,
            volume TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'polymarket',
            raw_payload TEXT NOT NULL,
            captured_at TEXT NOT NULL
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_event_store_timestamp ON event_store(timestamp)")


# ── Strategy Snapshots ──────────────────────────────────────────────────────


def init_strategy_tables(db: sqlite_utils.Database) -> None:
    """Create strategy_snapshots table if not exists. Idempotent."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS strategy_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            tick_number INTEGER NOT NULL,
            transition_counts TEXT NOT NULL,
            state_counts TEXT NOT NULL,
            warmup_ticks INTEGER NOT NULL,
            threshold_pct TEXT NOT NULL,
            snapshot_at TEXT NOT NULL,
            UNIQUE(strategy_name, domain, tick_number)
        )
        """
    )


def persist_strategy_snapshot(
    db: sqlite_utils.Database,
    domain: str,
    strategy_name: str,
    tick_number: int,
    transition_counts: list[list[int]],
    state_counts: list[int],
    warmup_ticks: int,
    threshold_pct: str | float,
) -> None:
    """Insert or replace a strategy snapshot row.

    The UNIQUE(strategy_name, domain, tick_number) constraint prevents
    duplicate tick entries. Uses INSERT OR REPLACE so re-processing the
    same tick overwrites the previous row.

    Args:
        db: Database instance.
        domain: Execution domain (e.g. ``"PM-5M"``).
        strategy_name: Strategy name (e.g. ``"markov_persistence"``).
        tick_number: Monotonically increasing tick identifier.
        transition_counts: 3×3 matrix as nested list.
        state_counts: Length-3 list of state visit counts.
        warmup_ticks: Warmup period used by the engine.
        threshold_pct: Threshold as string or float.
    """
    db["strategy_snapshots"].insert(  # type: ignore[union-attr]
        {
            "strategy_name": strategy_name,
            "domain": domain,
            "tick_number": tick_number,
            "transition_counts": json.dumps(transition_counts),
            "state_counts": json.dumps(state_counts),
            "warmup_ticks": warmup_ticks,
            "threshold_pct": str(threshold_pct),
            "snapshot_at": datetime.now(UTC).isoformat(),
        },
        pk="id",
        replace=True,
    )


def load_latest_snapshot(
    db: sqlite_utils.Database,
    domain: str,
    strategy_name: str,
) -> dict[str, Any] | None:
    """Load the latest snapshot for a (domain, strategy_name) pair.

    Args:
        db: Database instance.
        domain: Execution domain.
        strategy_name: Strategy name.

    Returns:
        Dict with snapshot columns, or ``None`` if no snapshot exists.
    """
    rows = list(
        db.query(
            "SELECT * FROM strategy_snapshots WHERE domain = ? AND strategy_name = ? ORDER BY tick_number DESC LIMIT 1",
            [domain, strategy_name],
        )
    )
    return rows[0] if rows else None


def append_event(db: sqlite_utils.Database, event: dict[str, Any]) -> int | None:
    """Insert event into event_store. Dedup via event_id UNIQUE constraint.

    Args:
        db: Database instance.
        event: Dict with keys: event_id, market_id, price, volume,
               timestamp, event_type, source (default 'polymarket').

    Returns:
        int | None: seq if inserted, None if duplicate (event_id exists).

    Raises:
        KeyError: If required keys missing from event dict.
    """
    cursor = db.execute(
        """INSERT OR IGNORE INTO event_store
           (event_id, market_id, price, volume, timestamp, event_type, source, raw_payload, captured_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            event["event_id"],
            event["market_id"],
            event["price"],
            event["volume"],
            event["timestamp"],
            event["event_type"],
            event.get("source", "polymarket"),
            event["raw_payload"],
            event.get("captured_at", datetime.now(UTC).isoformat()),
        ],
    )
    if cursor.rowcount == 0:
        return None
    row = db.execute("SELECT MAX(seq) FROM event_store").fetchone()
    return row[0] if row else None


def get_events(db: sqlite_utils.Database, since_seq: int = 0,
               limit: int = 100) -> list[MarketInput]:
    """Read events from store as MarketInput list.

    Args:
        db: Database instance.
        since_seq: Return events with seq > since_seq. Default 0 = all.
        limit: Max events to return. Default 100.

    Returns:
        list[MarketInput]: Ordered by seq ASC.

    Raises:
        ValueError: If since_seq < 0 or limit <= 0.
    """
    if since_seq < 0:
        raise ValueError("since_seq must be >= 0")
    if limit <= 0:
        raise ValueError("limit must be > 0")

    rows = db.query(
        "SELECT market_id, price, volume, timestamp, source FROM event_store WHERE seq > ? ORDER BY seq ASC LIMIT ?",
        [since_seq, limit],
    )
    return [
        MarketInput(
            market_id=row["market_id"],
            price=Decimal(row["price"]),
            volume=Decimal(row["volume"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            source=row["source"],
        )
        for row in rows
    ]


def get_max_seq(db: sqlite_utils.Database) -> int:
    """Get highest sequence number in event_store.

    Returns:
        int: MAX(seq), or 0 if table is empty.
    """
    cursor = db.execute("SELECT MAX(seq) FROM event_store")
    row = cursor.fetchone()
    return row[0] if row[0] is not None else 0


def count_events(db: sqlite_utils.Database) -> int:
    """Count total events in event_store.

    Returns:
        int: COUNT(*).
    """
    cursor = db.execute("SELECT COUNT(*) FROM event_store")
    row = cursor.fetchone()
    return int(row[0]) if row is not None else 0


def reset_event_store(db: sqlite_utils.Database) -> None:
    """DROP event_store and recreate. DEV ONLY.

    Destroys all captured data. Use only for development regeneration.
    """
    db.execute("DROP TABLE IF EXISTS event_store")
    init_event_store(db)


# ── Reflection Tables ─────────────────────────────────────────────────────────


def init_reflection_tables(db: sqlite_utils.Database) -> None:
    """Create reflection tables if they don't exist. Idempotent.

    Creates: reflection_reports, drift_events, proposals, reflection_config
    with corresponding indexes. Called from init_core_tables() or independently.
    """
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS reflection_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL,
            domain TEXT NOT NULL,
            mode TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            report_data TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reflection_reports_period
        ON reflection_reports(period_start, period_end)
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS drift_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            metric TEXT NOT NULL,
            previous_value REAL NOT NULL,
            current_value REAL NOT NULL,
            threshold REAL NOT NULL,
            deviation_pct REAL NOT NULL,
            detected_at TEXT NOT NULL DEFAULT (datetime('now')),
            acknowledged INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_drift_events_strategy_domain
        ON drift_events(strategy_id, domain)
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id TEXT NOT NULL,
            parameter_name TEXT NOT NULL,
            current_value REAL NOT NULL,
            proposed_value REAL NOT NULL,
            range_min REAL NOT NULL,
            range_max REAL NOT NULL,
            justification TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_proposals_strategy_id
        ON proposals(strategy_id)
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS reflection_config (
            domain TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (domain, key)
        )
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reflection_config_domain
        ON reflection_config(domain)
        """
    )
