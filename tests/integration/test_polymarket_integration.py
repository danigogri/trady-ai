"""Integration tests: WS mock → EventCapture → event_store → run_from_store → ExecutionResult."""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from trady_ai.adapters.polymarket import EventCapture
from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.engine import ExecutionEngine
from trady_ai.core.markov_strategy import MarkovStrategy
from trady_ai.core.models import MarketInput
from trady_ai.core.persistence import append_event, count_events, init_event_store

# ── Sample events ─────────────────────────────────────────────────────────────

EVENT_1 = {
    "market_id": "0xabc",
    "price": "0.65",
    "volume": "1500.00",
    "timestamp": "2026-07-08T12:00:00Z",
    "event_type": "tick",
}

EVENT_2 = {
    "market_id": "0xabc",
    "price": "0.66",
    "volume": "1600.00",
    "timestamp": "2026-07-08T12:01:00Z",
    "event_type": "tick",
}

EVENT_3 = {
    "market_id": "0xabc",
    "price": "0.64",
    "volume": "1400.00",
    "timestamp": "2026-07-08T12:02:00Z",
    "event_type": "tick",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_adapter():
    """PolymarketAdapter mock that translates events to MarketInput."""
    from trady_ai.adapters.polymarket import PolymarketAdapter

    adapter = MagicMock(spec=PolymarketAdapter)
    adapter.market_to_input.side_effect = lambda raw: MarketInput(
        market_id=raw["market_id"],
        price=Decimal(raw["price"]),
        volume=Decimal(raw["volume"]),
        timestamp=datetime.fromisoformat(raw["timestamp"]),
        source="polymarket",
    )
    adapter.subscribe_websocket.return_value = iter([])
    return adapter


def _populate_store(db, events: list[dict]) -> list[int]:
    """Insert events into event_store, return list of seq numbers."""
    init_event_store(db)
    seqs = []
    for ev in events:
        event_id = f"{ev['market_id']}:{ev['timestamp']}:{ev.get('event_type', 'tick')}"
        seq = append_event(db, {
            "event_id": event_id,
            "market_id": ev["market_id"],
            "price": ev["price"],
            "volume": ev["volume"],
            "timestamp": ev["timestamp"],
            "event_type": ev.get("event_type", "tick"),
            "source": "polymarket",
            "raw_payload": json.dumps(ev),
        })
        seqs.append(seq)
    return seqs


# ── TestCaptureToStorePipeline ────────────────────────────────────────────────


class TestCaptureToStorePipeline:
    """Full pipeline: mock WS → EventCapture → event_store → engine."""

    def test_capture_to_store_pipeline(self, mock_adapter, tmp_event_store_db):
        """WS mock → EventCapture._capture_one → event_store → run_from_store."""
        capture = EventCapture(mock_adapter, tmp_event_store_db)

        seq1 = capture._capture_one(EVENT_1)
        seq2 = capture._capture_one(EVENT_2)
        seq3 = capture._capture_one(EVENT_3)

        assert seq1 == 1
        assert seq2 == 2
        assert seq3 == 3
        assert count_events(tmp_event_store_db) == 3
        assert capture.last_seq == 3

        # Now run engine from store
        config = RuntimeConfig(
            warmup_ticks=5,
            threshold_pct=0.001,
            position_size=Decimal("10.00"),
            transaction_cost_pct=0.0,
            stop_loss_pct=0.05,
        )
        engine = ExecutionEngine(config, tmp_event_store_db, dry_run=True)
        strategy = MarkovStrategy(warmup_ticks=5, threshold_pct=0.001)

        result = engine.run_from_store(strategy, since_seq=0)

        assert len(result.signals) == 3
        assert result.summary_stats["total_signals"] == 3
        assert result.summary_stats["total_trades"] >= 0
        assert isinstance(result.summary_stats, dict)

    def test_dedup(self, mock_adapter, tmp_event_store_db):
        """Same event_id twice → only 1 row in event_store."""
        capture = EventCapture(mock_adapter, tmp_event_store_db)

        seq1 = capture._capture_one(EVENT_1)
        seq2 = capture._capture_one(EVENT_1)  # Duplicate

        assert seq1 == 1
        assert seq2 is None
        assert count_events(tmp_event_store_db) == 1

    def test_run_from_store_determinism(self, tmp_event_store_db):
        """Same event_store → run_from_store twice → identical ExecutionResult."""
        events = [EVENT_1, EVENT_2, EVENT_3]
        _populate_store(tmp_event_store_db, events)

        config = RuntimeConfig(
            warmup_ticks=2,
            threshold_pct=0.001,
            position_size=Decimal("10.00"),
            transaction_cost_pct=0.0,
            stop_loss_pct=0.05,
        )
        strategy1 = MarkovStrategy(warmup_ticks=2, threshold_pct=0.001)
        strategy2 = MarkovStrategy(warmup_ticks=2, threshold_pct=0.001)

        engine1 = ExecutionEngine(config, tmp_event_store_db, dry_run=True)
        result1 = engine1.run_from_store(strategy1, since_seq=0)

        # Fresh engine with same config, same db
        engine2 = ExecutionEngine(config, tmp_event_store_db, dry_run=True)
        result2 = engine2.run_from_store(strategy2, since_seq=0)

        # Compare signals
        for i, (s1, s2) in enumerate(zip(result1.signals, result2.signals)):
            assert s1.id == s2.id, f"Signal UUID mismatch at {i}"
            assert s1.direction == s2.direction, f"Signal direction mismatch at {i}"
            assert s1.confidence == pytest.approx(s2.confidence), f"Signal confidence mismatch at {i}"

        # Compare decisions
        for i, (d1, d2) in enumerate(zip(result1.decisions, result2.decisions)):
            assert d1.action == d2.action, f"Decision action mismatch at {i}"
            assert d1.reason == d2.reason, f"Decision reason mismatch at {i}"

        # Compare summary stats
        assert result1.summary_stats == result2.summary_stats

    def test_reconnect_snapshot_fill(self, mock_adapter, tmp_event_store_db):
        """WS disconnect → _handle_reconnect fetches current snapshot via REST."""
        mock_adapter.get_market_data.return_value = {
            "market_id": "0xabc",
            "price": "0.67",
            "volume": "1700.00",
            "timestamp": "2026-07-08T12:03:00Z",
            "best_bid": "0.66",
            "best_ask": "0.68",
        }

        # Pre-populate event_store with 2 events so MAX(seq) > 0
        capture = EventCapture(mock_adapter, tmp_event_store_db)
        capture._capture_one(EVENT_1)
        capture._capture_one(EVENT_2)

        assert count_events(tmp_event_store_db) == 2
        assert capture.last_seq == 2

        # Simulate reconnect: fetch current snapshot and capture it
        capture._handle_reconnect(["0xabc"])

        # Snapshot should have been captured as event seq=3
        assert count_events(tmp_event_store_db) == 3
        assert capture.last_seq == 3
        mock_adapter.get_market_data.assert_called_once_with("0xabc")

    def test_empty_store_run(self, tmp_event_store_db):
        """run_from_store with empty event_store → no errors, 0 signals."""
        init_event_store(tmp_event_store_db)

        config = RuntimeConfig(
            warmup_ticks=50,
            threshold_pct=0.001,
            position_size=Decimal("10.00"),
            transaction_cost_pct=0.0,
            stop_loss_pct=0.05,
        )
        strategy = MarkovStrategy(warmup_ticks=50, threshold_pct=0.001)
        engine = ExecutionEngine(config, tmp_event_store_db, dry_run=True)

        result = engine.run_from_store(strategy, since_seq=0)

        assert len(result.signals) == 0
        assert len(result.decisions) == 0
        assert len(result.trades) == 0
        assert result.summary_stats["total_signals"] == 0
        assert result.summary_stats["total_trades"] == 0
