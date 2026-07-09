"""Unit tests for EventCapture — thread lifecycle, dedup, reset."""
import time
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from trady_ai.adapters.polymarket import EventCapture
from trady_ai.core.models import MarketInput

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_adapter():
    """PolymarketAdapter mock with sensible defaults."""
    adapter = MagicMock()
    adapter.market_to_input.return_value = MarketInput(
        market_id="0xabc",
        price=Decimal("0.65"),
        volume=Decimal("1500.00"),
        timestamp=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
        source="polymarket",
    )
    return adapter


@pytest.fixture
def capture(mock_adapter, tmp_event_store_db):
    """EventCapture with mock adapter and tmp db."""
    return EventCapture(mock_adapter, tmp_event_store_db)


def _infinite_gen(*args, **kwargs):
    """Generator that yields events forever (every 10ms) for thread tests."""
    while True:
        yield {
            "market_id": "0xabc",
            "price": "0.65",
            "volume": "1500.00",
            "timestamp": "2026-07-08T12:00:00Z",
            "event_type": "tick",
        }
        time.sleep(0.01)


SAMPLE_EVENT = {
    "market_id": "0xabc",
    "price": "0.65",
    "volume": "1500.00",
    "timestamp": "2026-07-08T12:00:00Z",
    "event_type": "tick",
}


# ── TestStart ─────────────────────────────────────────────────────────────────


class TestStart:
    def test_start_spawns_thread(self, capture, mock_adapter):
        """start() spawns a daemon thread, is_running returns True."""
        mock_adapter.subscribe_websocket = _infinite_gen

        assert not capture.is_running
        capture.start(["0xabc"])
        time.sleep(0.05)  # Let thread start
        assert capture.is_running
        capture.stop()
        time.sleep(0.05)  # Let thread notice _running=False
        assert not capture.is_running

    def test_start_raises_if_running(self, capture, mock_adapter):
        """start() twice raises RuntimeError."""
        mock_adapter.subscribe_websocket = _infinite_gen

        capture.start(["0xabc"])
        time.sleep(0.05)

        with pytest.raises(RuntimeError, match="already running"):
            capture.start(["0xdef"])

        capture.stop()

    def test_start_empty_market_ids_raises(self, capture):
        """start([]) raises ValueError."""
        with pytest.raises(ValueError, match="market_ids"):
            capture.start([])


# ── TestStop ──────────────────────────────────────────────────────────────────


class TestStop:
    def test_stop_is_idempotent(self, capture):
        """stop() when not running is a no-op."""
        capture.stop()  # Should not raise


# ── TestCaptureOne ────────────────────────────────────────────────────────────


class TestCaptureOne:
    def test_capture_one_inserts_event(self, capture, mock_adapter):
        """_capture_one returns seq for a new event, store has 1 row."""
        seq = capture._capture_one(SAMPLE_EVENT)
        assert seq == 1
        from trady_ai.core.persistence import count_events

        assert count_events(capture._db) == 1

    def test_capture_one_deduplicates(self, capture, mock_adapter):
        """Same event_id twice → second returns None, store still has 1."""
        seq1 = capture._capture_one(SAMPLE_EVENT)
        assert seq1 == 1

        seq2 = capture._capture_one(SAMPLE_EVENT)
        assert seq2 is None

        from trady_ai.core.persistence import count_events

        assert count_events(capture._db) == 1


# ── TestReset ─────────────────────────────────────────────────────────────────


class TestReset:
    @patch("trady_ai.config.get_settings")
    def test_reset_only_in_dev(self, mock_get_settings, capture):
        """reset() raises RuntimeError in production."""
        mock_get_settings.return_value.environment = "production"
        with pytest.raises(RuntimeError, match="only available in development"):
            capture.reset()

    @patch("trady_ai.config.get_settings")
    def test_reset_drops_and_recreates(self, mock_get_settings, capture):
        """reset() in dev clears events and resets state."""
        mock_get_settings.return_value.environment = "development"

        capture._capture_one(SAMPLE_EVENT)
        assert capture._last_seq == 1

        capture.reset()

        assert capture._last_seq == 0
        from trady_ai.core.persistence import count_events

        assert count_events(capture._db) == 0


# ── TestError ─────────────────────────────────────────────────────────────────


class TestError:
    def test_error_property_returns_none_when_healthy(self, capture):
        """error property is None when no exception occurred."""
        assert capture.error is None
