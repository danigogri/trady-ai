import json
from datetime import datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from trady_ai.core.models import ExecutionDecision, MarketInput, MarketState, Signal, Trade
from trady_ai.core.persistence import (
    init_core_tables,
    load_execution_log,
    persist_execution_log,
    persist_signal,
    persist_trade,
)


class TestPersistenceRoundtrip:
    def test_signal_roundtrip(self, tmp_db):
        """Persist Signal → read from DB → compare fields."""
        init_core_tables(tmp_db)

        ts = datetime(2024, 6, 15, 14, 30, 0)
        signal = Signal(
            timestamp=ts,
            market_id="btc-usd",
            direction="LONG",
            confidence=0.85,
            strategy_name="markov_persistence",
            metadata={"source": "test"},
        )
        persist_signal(tmp_db, signal)

        rows = list(tmp_db["signals"].rows)
        assert len(rows) == 1

        row = rows[0]
        assert row["id"] == str(signal.id)
        assert row["timestamp"] == ts.isoformat()
        assert row["market_id"] == "btc-usd"
        assert row["direction"] == "LONG"
        assert row["confidence"] == 0.85
        assert row["strategy_name"] == "markov_persistence"
        assert json.loads(row["metadata"]) == {"source": "test"}

    def test_trade_roundtrip(self, tmp_db):
        """Persist Trade → read from DB → compare fields."""
        init_core_tables(tmp_db)

        ts = datetime(2024, 6, 15, 14, 30, 0)
        signal = Signal(
            timestamp=ts,
            market_id="btc-usd",
            direction="LONG",
            confidence=0.85,
            strategy_name="markov_persistence",
        )
        persist_signal(tmp_db, signal)

        trade = Trade(
            signal_id=signal.id,
            position_id=uuid5(NAMESPACE_URL, "position:btc-usd:test"),
            action="OPEN",
            price=Decimal("50000.00"),
            size=Decimal("10.00"),
            timestamp=ts,
            dry_run=True,
        )
        persist_trade(tmp_db, trade)

        rows = list(tmp_db["trades"].rows)
        assert len(rows) == 1

        row = rows[0]
        assert row["id"] == str(trade.id)
        assert row["action"] == "OPEN"
        assert row["price"] == "50000.00"
        assert row["size"] == "10.00"
        assert row["dry_run"] == 1

    def test_execution_log_roundtrip(self, tmp_db):
        """Persist execution_log → load → verify contents."""
        init_core_tables(tmp_db)

        ts = datetime(2024, 6, 15, 14, 30, 0)
        market_input = MarketInput(
            timestamp=ts,
            market_id="btc-usd",
            price=Decimal("50000.00"),
            volume=Decimal("100.50"),
        )
        state = MarketState(
            market_id="btc-usd",
            timestamp=ts,
            price=Decimal("50000.00"),
            volume=Decimal("100.50"),
            state="UP",
            previous_state=None,
        )
        signal = Signal(
            timestamp=ts,
            market_id="btc-usd",
            direction="LONG",
            confidence=0.85,
            strategy_name="markov_persistence",
        )
        decision = ExecutionDecision(
            signal_id=signal.id,
            action="OPEN_LONG",
            reason="Signal LONG approved",
            risk_check_passed=True,
            timestamp=ts,
        )
        trade = Trade(
            signal_id=signal.id,
            position_id=uuid5(NAMESPACE_URL, "position:btc-usd:test"),
            action="OPEN",
            price=Decimal("50000.00"),
            size=Decimal("10.00"),
            timestamp=ts,
        )

        persist_signal(tmp_db, signal)
        persist_trade(tmp_db, trade)
        persist_execution_log(tmp_db, 1, market_input, state, signal, decision, trade)

        log = load_execution_log(tmp_db)
        assert len(log) == 1
        entry = log[0]
        assert entry["tick_number"] == 1
        assert entry["market_id"] == "btc-usd"
        assert entry["decision_action"] == "OPEN_LONG"
        assert entry["trade_id"] == str(trade.id)


class TestPersistenceDecimalPrecision:
    def test_decimal_precision_preserved(self, tmp_db):
        """Decimal prices with many decimal places are preserved as strings."""
        init_core_tables(tmp_db)

        ts = datetime(2024, 6, 15, 14, 30, 0)
        signal = Signal(
            timestamp=ts,
            market_id="btc-usd",
            direction="NEUTRAL",
            confidence=0.0,
            strategy_name="markov_persistence",
        )

        # Precisión: 9 decimales
        precise_price = "100.123456789"
        trade = Trade(
            id=uuid5(NAMESPACE_URL, "trade:test:OPEN:2024-06-15T14:30:00"),
            signal_id=signal.id,
            position_id=uuid5(NAMESPACE_URL, "position:test"),
            action="OPEN",
            price=Decimal(precise_price),
            size=Decimal("10.00"),
            timestamp=ts,
        )

        persist_signal(tmp_db, signal)
        persist_trade(tmp_db, trade)

        rows = list(tmp_db["trades"].rows)
        assert rows[0]["price"] == precise_price


class TestPersistenceIdempotentInit:
    def test_init_core_tables_twice(self, tmp_db):
        """Calling init_core_tables twice does not raise."""
        init_core_tables(tmp_db)
        # Segunda llamada — debe ser idempotente
        init_core_tables(tmp_db)

        # Verify all 5 tables exist
        tables = tmp_db.table_names()
        for tbl in ("signals", "positions", "trades", "execution_log", "market_states"):
            assert tbl in tables

    def test_init_on_new_db(self, tmp_path):
        """init_core_tables works on a freshly initialized DB."""
        from trady_ai.db.database import init_db

        db = init_db(tmp_path / "core_test.db")
        init_core_tables(db)

        tables = db.table_names()
        for tbl in ("signals", "positions", "trades", "execution_log", "market_states"):
            assert tbl in tables, f"Table {tbl} should exist after init_core_tables"
