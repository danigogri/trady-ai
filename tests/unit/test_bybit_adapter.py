"""Unit tests for BybitAdapter — strict TDD (RED first).

Tests cover market_to_input (pure function) mapping, constructor,
and subscribe_websocket WebSocket integration.

Ref spec: openspec/changes/bybit-adapter/specs/bybit-adapter/spec.md
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, DecimalException

import pytest

from trady_ai.core.models import MarketInput

# ── 1.1 market_to_input (pure function) ──────────────────────────────────────


class TestMarketToInput:
    """REQ-BB-003: Bybit trade to MarketInput mapping.

    MarketInput fields derived from Bybit trade event:
      T (int epoch ms) → timestamp
      s (str) → market_id (UPPERCASE)
      p (str) → price (Decimal)
      v (str) → volume (Decimal)
      (static) → source="bybit"
    """

    def test_valid_trade_event(self):
        """Happy path: valid Bybit trade → correct MarketInput."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "BTCUSDT",
            "p": "98765.43",
            "v": "0.00123",
        }
        result = BybitAdapter.market_to_input(raw)

        assert isinstance(result, MarketInput)
        assert result.timestamp == datetime(2025, 7, 8, 18, 40, 0, tzinfo=UTC)
        assert result.market_id == "BTCUSDT"
        assert result.price == Decimal("98765.43")
        assert result.volume == Decimal("0.00123")
        assert result.source == "bybit"

    def test_missing_key_raises_keyerror(self):
        """Missing required key T or v → KeyError."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {"s": "BTCUSDT", "p": "50000"}
        with pytest.raises(KeyError):
            BybitAdapter.market_to_input(raw)

    def test_missing_s_raises_keyerror(self):
        """Missing 's' (market_id) key → KeyError."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {"T": 1752000000000, "p": "50000", "v": "0.001"}
        with pytest.raises(KeyError):
            BybitAdapter.market_to_input(raw)

    def test_invalid_decimal_raises_valueerror(self):
        """Non-numeric p or v → ValueError."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "BTCUSDT",
            "p": "not_a_number",
            "v": "0.001",
        }
        with pytest.raises((ValueError, DecimalException)):
            BybitAdapter.market_to_input(raw)

    def test_invalid_volume_decimal_raises(self):
        """Non-numeric v → ValueError."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "BTCUSDT",
            "p": "50000",
            "v": "bad_volume",
        }
        with pytest.raises((ValueError, DecimalException)):
            BybitAdapter.market_to_input(raw)

    def test_idempotent_mapping(self):
        """Same input → same output every time (REQ-BB-007)."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "BTCUSDT",
            "p": "98765.43",
            "v": "0.00123",
        }
        first = BybitAdapter.market_to_input(raw)
        second = BybitAdapter.market_to_input(raw)
        assert first == second

    def test_uppercase_symbol_preserved(self):
        """Market id is uppercased (Bybit returns UPPERCASE)."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "ETHUSDT",
            "p": "3500.50",
            "v": "2.500",
        }
        result = BybitAdapter.market_to_input(raw)
        assert result.market_id == "ETHUSDT"

    def test_lowercase_symbol_gets_uppercased(self):
        """Even if Bybit sends lowercase s, we uppercase it."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "btcusdt",
            "p": "50000",
            "v": "0.001",
        }
        result = BybitAdapter.market_to_input(raw)
        assert result.market_id == "BTCUSDT"

    def test_large_volume_decimal(self):
        """Volume with many decimal places is handled."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "BTCUSDT",
            "p": "50000.00",
            "v": "12345.67890123",
        }
        result = BybitAdapter.market_to_input(raw)
        assert result.volume == Decimal("12345.67890123")
        assert result.price == Decimal("50000.00")

    def test_empty_string_price_raises(self):
        """Empty string for p → Decimal('') raises."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "BTCUSDT",
            "p": "",
            "v": "0.001",
        }
        with pytest.raises((ValueError, DecimalException)):
            BybitAdapter.market_to_input(raw)

    def test_null_values_raises(self):
        """None for p or v → TypeError or similar raises."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {
            "T": 1752000000000,
            "s": "BTCUSDT",
            "p": None,
            "v": "0.001",
        }
        with pytest.raises((TypeError, ValueError)):
            BybitAdapter.market_to_input(raw)

    def test_missing_p_raises_keyerror(self):
        """Missing 'p' (price) key → KeyError."""
        from trady_ai.adapters.bybit import BybitAdapter

        raw = {"T": 1752000000000, "s": "BTCUSDT", "v": "0.001"}
        with pytest.raises(KeyError):
            BybitAdapter.market_to_input(raw)


# ── 1.2 Constructor and subscribe_websocket ──────────────────────────────────


class TestConstructor:
    """REQ-BB-001: Constructor stores ws_url and rest_url."""

    def test_constructor_stores_urls(self):
        """Constructor sets ws_url and rest_url attributes."""
        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )
        assert adapter._ws_url == "wss://stream-testnet.bybit.com/v5/public/spot"
        assert adapter._rest_url == "https://api-testnet.bybit.com"


class TestSubscribeWebSocket:
    """REQ-BB-002: WebSocket subscribe behavior."""

    def test_empty_symbols_raises_valueerror(self):
        """Empty symbol list raises ValueError."""
        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )
        with pytest.raises(ValueError, match="symbols must not be empty"):
            next(adapter.subscribe_websocket([]))

    def test_subscribe_single_symbol(self):
        """Single symbol → subscribe with publicTrade.BTCUSDT, yield single trade."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        sent_messages = []

        async def mock_send(msg):
            sent_messages.append(msg)

        mock_ws = AsyncMock()
        mock_ws.send = mock_send
        mock_ws.__aiter__.return_value = [
            json.dumps({
                "topic": "publicTrade.BTCUSDT",
                "type": "snapshot",
                "ts": 1752000000000,
                "data": [
                    {"T": 1752000000000, "s": "BTCUSDT", "p": "98765.43", "v": "0.00123"},
                ],
            })
        ]

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["BTCUSDT"])
            events = list(gen)

        # Verify subscribe message
        assert len(sent_messages) == 1
        payload = json.loads(sent_messages[0])
        assert payload["op"] == "subscribe"
        assert payload["args"] == ["publicTrade.BTCUSDT"]

        # Verify yielded events
        assert len(events) == 1
        assert events[0]["s"] == "BTCUSDT"
        assert events[0]["T"] == 1752000000000
        assert events[0]["p"] == "98765.43"
        assert events[0]["v"] == "0.00123"

    def test_subscribe_multi_batch(self):
        """Multi-element data[] yields one dict per trade."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [
            json.dumps({
                "topic": "publicTrade.BTCUSDT",
                "type": "snapshot",
                "ts": 1752000000000,
                "data": [
                    {"T": 1752000000001, "s": "BTCUSDT", "p": "98765.43", "v": "0.00123"},
                    {"T": 1752000000002, "s": "BTCUSDT", "p": "98766.00", "v": "0.00200"},
                    {"T": 1752000000003, "s": "BTCUSDT", "p": "98767.50", "v": "0.00150"},
                ],
            })
        ]

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["BTCUSDT"])
            events = list(gen)

        assert len(events) == 3
        assert events[0]["p"] == "98765.43"
        assert events[1]["p"] == "98766.00"
        assert events[2]["p"] == "98767.50"
        assert events[0]["T"] == 1752000000001
        assert events[1]["T"] == 1752000000002
        assert events[2]["T"] == 1752000000003

    def test_subscribe_multi_symbol(self):
        """Multiple symbols → args contain both publicTrade streams."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        sent_messages = []

        async def mock_send(msg):
            sent_messages.append(msg)

        mock_ws = AsyncMock()
        mock_ws.send = mock_send
        mock_ws.__aiter__.return_value = iter([])

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["BTCUSDT", "ETHUSDT"])
            list(gen)  # exhaust

        assert len(sent_messages) == 1
        payload = json.loads(sent_messages[0])
        assert payload["op"] == "subscribe"
        assert set(payload["args"]) == {"publicTrade.BTCUSDT", "publicTrade.ETHUSDT"}

    def test_non_json_message_skipped(self):
        """Non-JSON WS message is logged+warn and skipped."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [
            "plain text ping",
            json.dumps({
                "topic": "publicTrade.BTCUSDT",
                "type": "snapshot",
                "data": [
                    {"T": 1752000000000, "s": "BTCUSDT", "p": "50000", "v": "1.0"},
                ],
            }),
        ]

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["BTCUSDT"])
            events = list(gen)

        assert len(events) == 1
        assert events[0]["s"] == "BTCUSDT"

    def test_empty_data_array_yields_nothing(self):
        """Empty data[] array → nothing yielded."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [
            json.dumps({
                "topic": "publicTrade.BTCUSDT",
                "type": "snapshot",
                "data": [],
            })
        ]

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["BTCUSDT"])
            events = list(gen)

        assert len(events) == 0

    def test_missing_data_key_yields_nothing(self):
        """Message without data key → nothing yielded, no crash."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [
            json.dumps({
                "topic": "publicTrade.BTCUSDT",
                "type": "snapshot",
            })
        ]

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["BTCUSDT"])
            events = list(gen)

        assert len(events) == 0

    def test_connection_failure_propagates(self):
        """ConnectionError from WS → generator yields empty (error logged, not raised sync)."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        with patch("websockets.connect", side_effect=ConnectionError("refused")):
            gen = adapter.subscribe_websocket(["BTCUSDT"])
            events = list(gen)

        # Generator yields empty on connection failure (error logged internally)
        assert len(events) == 0

    def test_graceful_disconnect_ends_generator(self):
        """WS closes cleanly → generator stops without exception."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [
            json.dumps({
                "topic": "publicTrade.BTCUSDT",
                "type": "snapshot",
                "data": [{"T": 1752000000000, "s": "BTCUSDT", "p": "50000", "v": "0.001"}],
            })
        ]

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["BTCUSDT"])
            events = list(gen)

        assert len(events) == 1
        assert events[0]["p"] == "50000"

    def test_server_initiated_close_stops_generator(self):
        """Server closes WS mid-stream → generator yields what was received, then stops."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.bybit import BybitAdapter
        import websockets

        adapter = BybitAdapter(
            ws_url="wss://stream-testnet.bybit.com/v5/public/spot",
            rest_url="https://api-testnet.bybit.com",
        )

        mock_ws = AsyncMock()
        mock_ws.__aiter__.side_effect = websockets.ConnectionClosed(None, None)

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["BTCUSDT"])
            events = list(gen)

        # Generator should stop gracefully on ConnectionClosed
        assert len(events) == 0
