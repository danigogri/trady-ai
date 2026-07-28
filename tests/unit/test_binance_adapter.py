"""Unit tests for BinanceAdapter — strict TDD (RED first).

Tests cover market_to_input (pure function) mapping, constructor,
and subscribe_websocket WebSocket integration.

Per Stict TDD: write tests FIRST, then implement the minimum code to pass.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, DecimalException

import pytest

from trady_ai.core.models import MarketInput

# ── 1.1 market_to_input (pure function) ──────────────────────────────────────


class TestMarketToInput:
    """REQ-BA-003: Trade to MarketInput mapping.

    MarketInput fields derived from Binance trade event:
      E (int epoch ms) → timestamp
      s (str) → market_id (lowercase)
      p (str) → price (Decimal)
      q (str) → volume (Decimal)
      (static) → source="binance"
    """

    def test_valid_trade_event(self):
        """Happy path: valid Binance trade → correct MarketInput."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {
            "e": "trade",
            "E": 1752000000000,
            "s": "BTCUSDT",
            "p": "98765.43",
            "q": "0.00123",
        }
        result = BinanceAdapter.market_to_input(raw)

        assert isinstance(result, MarketInput)
        assert result.timestamp == datetime(2025, 7, 8, 18, 40, 0, tzinfo=UTC)
        assert result.market_id == "btcusdt"
        assert result.price == Decimal("98765.43")
        assert result.volume == Decimal("0.00123")
        assert result.source == "binance"

    def test_missing_key_raises_keyerror(self):
        """Missing required key E or q → KeyError."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {"e": "trade", "s": "BTCUSDT", "p": "50000"}
        with pytest.raises(KeyError):
            BinanceAdapter.market_to_input(raw)

    def test_invalid_decimal_raises_valueerror(self):
        """Non-numeric p or q → ValueError."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {
            "E": 1752000000000,
            "s": "BTCUSDT",
            "p": "not_a_number",
            "q": "0.001",
        }
        with pytest.raises((ValueError, DecimalException)):
            BinanceAdapter.market_to_input(raw)

    def test_idempotent_mapping(self):
        """Same input → same output every time (REQ-BA-006)."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {
            "e": "trade",
            "E": 1752000000000,
            "s": "BTCUSDT",
            "p": "98765.43",
            "q": "0.00123",
        }
        first = BinanceAdapter.market_to_input(raw)
        second = BinanceAdapter.market_to_input(raw)
        assert first == second

    def test_lowercase_symbol_preserved(self):
        """Market id is lowercased."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {
            "e": "trade",
            "E": 1752000000000,
            "s": "ETHUSDT",
            "p": "3500.50",
            "q": "2.500",
        }
        result = BinanceAdapter.market_to_input(raw)
        assert result.market_id == "ethusdt"

    def test_large_volume_decimal(self):
        """Volume with many decimal places is handled."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {
            "e": "trade",
            "E": 1752000000000,
            "s": "BTCUSDT",
            "p": "50000.00",
            "q": "12345.67890123",
        }
        result = BinanceAdapter.market_to_input(raw)
        assert result.volume == Decimal("12345.67890123")
        assert result.price == Decimal("50000.00")

    def test_missing_s_raises_keyerror(self):
        """Missing 's' (market_id) key → KeyError."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {"e": "trade", "E": 1752000000000, "p": "50000", "q": "0.001"}
        with pytest.raises(KeyError):
            BinanceAdapter.market_to_input(raw)

    def test_empty_string_price_raises(self):
        """Empty string for p → Decimal('') raises."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {
            "e": "trade",
            "E": 1752000000000,
            "s": "BTCUSDT",
            "p": "",
            "q": "0.001",
        }
        with pytest.raises((ValueError, DecimalException)):
            BinanceAdapter.market_to_input(raw)

    def test_null_values_raises(self):
        """None for p or q → TypeError or Decimal(None) raises."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {
            "e": "trade",
            "E": 1752000000000,
            "s": "BTCUSDT",
            "p": None,
            "q": "0.001",
        }
        with pytest.raises((TypeError, ValueError)):
            BinanceAdapter.market_to_input(raw)
        """None for p or q → TypeError or Decimal(None) raises."""
        from trady_ai.adapters.binance import BinanceAdapter

        raw = {
            "e": "trade",
            "E": 1752000000000,
            "s": "BTCUSDT",
            "p": None,
            "q": "0.001",
        }
        with pytest.raises((TypeError, ValueError)):
            BinanceAdapter.market_to_input(raw)


# ── 1.2 Constructor and subscribe_websocket ──────────────────────────────────


class TestConstructor:
    """REQ-BA-001: Constructor stores ws_url and rest_url."""

    def test_constructor_stores_urls(self):
        """Constructor sets ws_url and rest_url attributes."""
        from trady_ai.adapters.binance import BinanceAdapter

        adapter = BinanceAdapter(
            ws_url="wss://testnet.binance.vision/ws",
            rest_url="https://testnet.binance.vision",
        )
        assert adapter._ws_url == "wss://testnet.binance.vision/ws"
        assert adapter._rest_url == "https://testnet.binance.vision"


class TestSubscribeWebSocket:
    """REQ-BA-002: WebSocket subscribe behavior."""

    def test_empty_symbols_raises_valueerror(self):
        """Empty symbol list raises ValueError."""
        from trady_ai.adapters.binance import BinanceAdapter

        adapter = BinanceAdapter(
            ws_url="wss://testnet.binance.vision/ws",
            rest_url="https://testnet.binance.vision",
        )
        with pytest.raises(ValueError, match="symbols must not be empty"):
            next(adapter.subscribe_websocket([]))

    def test_ws_connect_and_subscribe(self):
        """AsyncMock: connect, send SUBSCRIBE, yield parsed dict."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.binance import BinanceAdapter

        adapter = BinanceAdapter(
            ws_url="wss://testnet.binance.vision/ws",
            rest_url="https://testnet.binance.vision",
        )

        # Simulate WS messages
        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [
            json.dumps({
                "e": "trade",
                "E": 1752000000000,
                "s": "BTCUSDT",
                "p": "98765.43",
                "q": "0.00123",
            })
        ]

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["btcusdt"])
            events = list(gen)

        assert len(events) == 1
        assert events[0]["e"] == "trade"
        assert events[0]["s"] == "BTCUSDT"

    def test_subscribe_multi_symbol(self):
        """Multiple symbols → params with all @trade streams."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.binance import BinanceAdapter

        adapter = BinanceAdapter(
            ws_url="wss://testnet.binance.vision/ws",
            rest_url="https://testnet.binance.vision",
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
            gen = adapter.subscribe_websocket(["btcusdt", "ethusdt"])
            list(gen)  # exhaust

        assert len(sent_messages) == 1
        payload = json.loads(sent_messages[0])
        assert payload["method"] == "SUBSCRIBE"
        assert set(payload["params"]) == {"btcusdt@trade", "ethusdt@trade"}
        assert payload["id"] == 1

    def test_non_json_message_skipped(self):
        """Non-JSON WS message is logged+warn and skipped."""
        from unittest.mock import AsyncMock, patch

        from trady_ai.adapters.binance import BinanceAdapter

        adapter = BinanceAdapter(
            ws_url="wss://testnet.binance.vision/ws",
            rest_url="https://testnet.binance.vision",
        )

        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [
            "plain text ping",
            json.dumps({"e": "trade", "E": 1752000000000, "s": "BTCUSDT", "p": "50000", "q": "1.0"}),
        ]

        with patch("websockets.connect", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_ws)
        )):
            gen = adapter.subscribe_websocket(["btcusdt"])
            events = list(gen)

        assert len(events) == 1
        assert events[0]["s"] == "BTCUSDT"
