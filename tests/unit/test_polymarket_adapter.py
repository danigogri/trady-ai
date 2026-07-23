"""Unit tests for PolymarketAdapter — stateless, no network, mock boundaries."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest

from trady_ai.adapters.polymarket import PolymarketAdapter
from trady_ai.core.models import MarketInput, Trade

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def adapter():
    """PolymarketAdapter with test URLs (no mocking, no HTTP calls made)."""
    return PolymarketAdapter(
        rest_url="https://test.api.com",
        ws_url="wss://test.ws.com",
    )


@pytest.fixture
def sample_raw_market():
    """Valid Polymarket market data dict."""
    return {
        "market_id": "0xabc",
        "price": "0.65",
        "volume": "1500.00",
        "timestamp": "2026-07-08T12:00:00Z",
    }


@pytest.fixture
def sample_raw_order():
    """Valid Polymarket order response dict."""
    return {
        "order_id": "ord-123",
        "status": "OPEN",
        "market_id": "0xabc",
        "side": "BUY",
        "price": "0.65",
        "size": "100.00",
        "order_type": "GTC",
        "timestamp": "2026-07-08T12:00:00Z",
    }


# ── Mock WS helper for subscribe_websocket tests ──────────────────────────────


class _AsyncMockWS:
    """Mock async context manager + async iterable for websockets testing.

    Supports ``async with`` and ``async for`` protocols so it can replace
    the websockets.connect() return value in tests.
    """

    def __init__(self, messages: list[str]):
        self.messages = messages
        self.sent_messages: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self._async_gen().__aiter__()

    async def _async_gen(self):
        for msg in self.messages:
            yield msg

    async def send(self, msg: str) -> None:
        self.sent_messages.append(msg)


# ── TestInit ──────────────────────────────────────────────────────────────────


class TestInit:
    def test_init_stores_config(self):
        """Adapter stores REST URL, WS URL, and optional API key."""
        adapter = PolymarketAdapter(
            rest_url="https://clob.polymarket.com",
            ws_url="wss://ws.polymarket.com/ws",
            api_key="key-123",
            secret="secret-456",
            passphrase="phrase-789",
        )
        assert adapter._rest_url == "https://clob.polymarket.com"
        assert adapter._ws_url == "wss://ws.polymarket.com/ws"
        assert adapter._secret == "secret-456"
        assert adapter._passphrase == "phrase-789"

    def test_init_creates_httpx_client(self, adapter):
        """Adapter creates an httpx.Client during init."""
        assert isinstance(adapter._client, httpx.Client)

    def test_init_sets_auth_header_when_api_key_provided(self):
        """When api_key is provided, POLY-API-KEY header is set."""
        with patch("trady_ai.adapters.polymarket.httpx.Client") as mock_client:
            PolymarketAdapter(
                rest_url="https://test.com",
                ws_url="wss://test.com",
                api_key="test-key",
            )
            _call_kwargs = mock_client.call_args.kwargs
            assert _call_kwargs["headers"].get("POLY-API-KEY") == "test-key"

    def test_init_no_auth_header_without_api_key(self, adapter):
        """When api_key is empty, no POLY-API-KEY header is sent."""
        # The adapter fixture has no api_key, so no auth header expected.
        # We directly check the client's headers (may be empty dict).
        headers = adapter._client.headers
        assert "POLY-API-KEY" not in headers


# ── TestMarketToInput ─────────────────────────────────────────────────────────


class TestMarketToInput:
    def test_market_to_input(self, adapter, sample_raw_market):
        """Maps valid raw dict to MarketInput with source='polymarket'."""
        result = adapter.market_to_input(sample_raw_market)

        assert isinstance(result, MarketInput)
        assert result.market_id == "0xabc"
        assert result.price == Decimal("0.65")
        assert result.volume == Decimal("1500.00")
        assert result.timestamp == datetime(2026, 7, 8, 12, 0, tzinfo=UTC)
        assert result.source == "polymarket"

    def test_market_to_input_missing_keys(self, adapter, sample_raw_market):
        """Missing required key raises KeyError."""
        bad = dict(sample_raw_market)
        del bad["price"]
        with pytest.raises(KeyError, match="price"):
            adapter.market_to_input(bad)

    def test_market_to_input_missing_multiple_keys(self, adapter):
        """Multiple missing keys raises KeyError on the first missing."""
        with pytest.raises(KeyError):
            adapter.market_to_input({"market_id": "0xabc"})

    def test_market_to_input_invalid_price(self, adapter, sample_raw_market):
        """Invalid (non-numeric) price raises exception (ValueError or decimal)."""
        import decimal

        bad = dict(sample_raw_market, price="not-a-number")
        with pytest.raises((ValueError, decimal.InvalidOperation)):
            adapter.market_to_input(bad)

    def test_market_to_input_invalid_timestamp(self, adapter, sample_raw_market):
        """Invalid ISO timestamp raises ValueError."""
        bad = dict(sample_raw_market, timestamp="not-a-date")
        with pytest.raises(ValueError):
            adapter.market_to_input(bad)

    def test_market_to_input_is_pure_function(self, adapter, sample_raw_market):
        """Same input always produces same output (pure function)."""
        r1 = adapter.market_to_input(sample_raw_market)
        r2 = adapter.market_to_input(sample_raw_market)
        assert r1 == r2


# ── TestOrderToTrade ──────────────────────────────────────────────────────────


class TestOrderToTrade:
    def test_order_to_trade_buy(self, adapter, sample_raw_order):
        """BUY order maps to Trade with action='OPEN'."""
        signal_id = "00000000-0000-0000-0000-000000000001"
        position_id = "00000000-0000-0000-0000-000000000002"

        trade = adapter.order_to_trade(
            sample_raw_order,
            signal_id=signal_id,
            position_id=position_id,
            dry_run=True,
        )

        assert isinstance(trade, Trade)
        assert trade.action == "OPEN"
        assert trade.price == Decimal("0.65")
        assert trade.size == Decimal("100.00")
        assert trade.dry_run is True
        assert trade.timestamp == datetime(2026, 7, 8, 12, 0, tzinfo=UTC)

    def test_order_to_trade_sell(self, adapter, sample_raw_order):
        """SELL order maps to Trade with action='CLOSE'."""
        sell_order = dict(sample_raw_order, side="SELL")

        trade = adapter.order_to_trade(
            sell_order,
            signal_id="00000000-0000-0000-0000-000000000001",
            position_id="00000000-0000-0000-0000-000000000002",
            dry_run=False,
        )

        assert trade.action == "CLOSE"
        assert trade.dry_run is False

    def test_order_to_trade_defaults_to_open(self, adapter, sample_raw_order):
        """Missing 'side' key defaults to action='OPEN'."""
        no_side = dict(sample_raw_order)
        del no_side["side"]

        trade = adapter.order_to_trade(
            no_side,
            signal_id="00000000-0000-0000-0000-000000000001",
            position_id="00000000-0000-0000-0000-000000000002",
            dry_run=True,
        )

        assert trade.action == "OPEN"

    def test_order_to_trade_missing_keys(self, adapter, sample_raw_order):
        """Missing required key (e.g. price) raises KeyError."""
        bad = dict(sample_raw_order)
        del bad["price"]
        with pytest.raises(KeyError, match="price"):
            adapter.order_to_trade(bad, signal_id="x", position_id="y", dry_run=True)


# ── TestPlaceOrder Validation ─────────────────────────────────────────────────


class TestPlaceOrderValidation:
    def test_place_order_validates_side(self, adapter):
        """side='INVALID' raises ValueError WITHOUT making HTTP request."""
        with pytest.raises(ValueError, match="side must be BUY or SELL"):
            adapter.place_order("0xabc", "INVALID", Decimal("0.5"), Decimal("10"))

    def test_place_order_validates_empty_market_id(self, adapter):
        """Empty market_id raises ValueError."""
        with pytest.raises(ValueError, match="market_id must not be empty"):
            adapter.place_order("", "BUY", Decimal("0.5"), Decimal("10"))

    def test_place_order_validates_price_zero(self, adapter):
        """Zero price raises ValueError."""
        with pytest.raises(ValueError, match="price must be > 0"):
            adapter.place_order("0xabc", "BUY", Decimal("0"), Decimal("10"))

    def test_place_order_validates_size_zero(self, adapter):
        """Zero size raises ValueError."""
        with pytest.raises(ValueError, match="size must be > 0"):
            adapter.place_order("0xabc", "BUY", Decimal("0.5"), Decimal("0"))


# ── TestREST HTTP calls (mocked httpx) ────────────────────────────────────────


class TestPlaceOrderHTTP:
    @patch("trady_ai.adapters.polymarket.httpx.Client")
    def test_place_order_makes_request(self, mock_client):
        """place_order POSTs to /order with correct payload."""
        mock_instance = mock_client.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "order_id": "ord-123",
            "status": "OPEN",
            "market_id": "0xabc",
            "side": "BUY",
            "price": "0.65",
            "size": "100.00",
            "order_type": "GTC",
            "timestamp": "2026-07-08T12:00:00Z",
        }
        mock_instance.post.return_value = mock_response

        a = PolymarketAdapter("https://test.com", "wss://test.com")
        result = a.place_order("0xabc", "BUY", Decimal("0.65"), Decimal("100.00"))

        assert result["order_id"] == "ord-123"
        mock_instance.post.assert_called_once_with(
            "/order",
            json={
                "market": "0xabc",
                "side": "BUY",
                "price": "0.65",
                "size": "100.00",
                "order_type": "GTC",
            },
        )


class TestGetMarkets:
    @patch("trady_ai.adapters.polymarket.httpx.Client")
    def test_get_markets_makes_request(self, mock_client):
        """get_markets GETs /markets and returns parsed list."""
        mock_instance = mock_client.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"condition_id": "0x123", "question": "Will X happen?"},
        ]
        mock_instance.get.return_value = mock_response

        a = PolymarketAdapter("https://test.com", "wss://test.com")
        result = a.get_markets()

        assert len(result) == 1
        assert result[0]["condition_id"] == "0x123"
        mock_instance.get.assert_called_once_with("/markets")


class TestGetMarketData:
    @patch("trady_ai.adapters.polymarket.httpx.Client")
    def test_get_market_data_makes_request(self, mock_client):
        """get_market_data GETs /markets/{id} with correct ID."""
        mock_instance = mock_client.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "market_id": "0xabc",
            "price": "0.65",
            "volume": "1500",
            "timestamp": "2026-07-08T12:00:00Z",
        }
        mock_instance.get.return_value = mock_response

        a = PolymarketAdapter("https://test.com", "wss://test.com")
        result = a.get_market_data("0xabc")

        assert result["market_id"] == "0xabc"
        mock_instance.get.assert_called_once_with("/markets/0xabc")

    @patch("trady_ai.adapters.polymarket.httpx.Client")
    def test_get_market_data_empty_id_raises(self, mock_client):
        """Empty market_id raises ValueError without HTTP."""
        a = PolymarketAdapter("https://test.com", "wss://test.com")
        with pytest.raises(ValueError, match="market_id must not be empty"):
            a.get_market_data("")


class TestGetOrderBook:
    @patch("trady_ai.adapters.polymarket.httpx.Client")
    def test_get_order_book_makes_request(self, mock_client):
        """get_order_book GETs /order-book with market param."""
        mock_instance = mock_client.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "market_id": "0xabc",
            "bids": [{"price": "0.65", "size": "100"}],
            "asks": [],
            "timestamp": "2026-07-08T12:00:00Z",
        }
        mock_instance.get.return_value = mock_response

        a = PolymarketAdapter("https://test.com", "wss://test.com")
        result = a.get_order_book("0xabc")

        assert result["market_id"] == "0xabc"
        assert len(result["bids"]) == 1
        mock_instance.get.assert_called_once_with(
            "/order-book",
            params={"market": "0xabc"},
        )


class TestCancelOrder:
    @patch("trady_ai.adapters.polymarket.httpx.Client")
    def test_cancel_order_makes_request(self, mock_client):
        """cancel_order DELETEs /order/{id}."""
        mock_instance = mock_client.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "order_id": "ord-123",
            "status": "CANCELLED",
            "timestamp": "2026-07-08T12:00:00Z",
        }
        mock_instance.delete.return_value = mock_response

        a = PolymarketAdapter("https://test.com", "wss://test.com")
        result = a.cancel_order("ord-123")

        assert result["status"] == "CANCELLED"
        mock_instance.delete.assert_called_once_with("/order/ord-123")

    @patch("trady_ai.adapters.polymarket.httpx.Client")
    def test_cancel_order_empty_id_raises(self, mock_client):
        """Empty order_id raises ValueError without HTTP."""
        a = PolymarketAdapter("https://test.com", "wss://test.com")
        with pytest.raises(ValueError, match="order_id must not be empty"):
            a.cancel_order("")


class TestGetOpenOrders:
    @patch("trady_ai.adapters.polymarket.httpx.Client")
    def test_get_open_orders_makes_request(self, mock_client):
        """get_open_orders GETs /orders with market and status=OPEN."""
        mock_instance = mock_client.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "order_id": "ord-123",
                "market_id": "0xabc",
                "side": "BUY",
                "price": "0.65",
                "size": "100.00",
                "status": "OPEN",
                "timestamp": "2026-07-08T12:00:00Z",
            },
        ]
        mock_instance.get.return_value = mock_response

        a = PolymarketAdapter("https://test.com", "wss://test.com")
        result = a.get_open_orders("0xabc")

        assert len(result) == 1
        assert result[0]["order_id"] == "ord-123"
        mock_instance.get.assert_called_once_with(
            "/orders",
            params={"market": "0xabc", "status": "OPEN"},
        )


# ── Test WebSocket ────────────────────────────────────────────────────────────


class TestSubscribeWebSocket:
    def test_subscribe_websocket_empty_ids(self, adapter):
        """Empty market_ids raises ValueError."""
        with pytest.raises(ValueError, match="market_ids must not be empty"):
            list(adapter.subscribe_websocket([]))

    @patch("trady_ai.adapters.polymarket.websockets.connect")
    def test_subscribe_websocket_yields_events(self, mock_connect, adapter):
        """subscribe_websocket yields normalized events from WS book snapshots."""
        # Polymarket sends a LIST of book snapshot objects per message.
        messages = [
            json.dumps(
                [
                    {
                        "market": "0xabc",
                        "asset_id": "tok1",
                        "timestamp": "1784742965886",  # ms epoch
                        "bids": [{"price": "0.01", "size": "100"}],
                        "asks": [{"price": "0.99", "size": "200"}],
                        "last_trade_price": "0.70",
                        "event_type": "book",
                        "hash": "h1",
                    }
                ]
            ),
            json.dumps(
                [
                    {
                        "market": "0xdef",
                        "asset_id": "tok2",
                        "timestamp": "1784743026000",
                        "bids": [],
                        "asks": [],
                        "last_trade_price": "0.85",
                        "event_type": "book",
                        "hash": "h2",
                    }
                ]
            ),
        ]
        mock_ws = _AsyncMockWS(messages)
        mock_connect.return_value = mock_ws

        events = list(adapter.subscribe_websocket(["tok1"]))

        assert len(events) == 2
        assert events[0]["market_id"] == "0xabc"
        assert events[0]["asset_id"] == "tok1"
        assert events[0]["price"] == "0.70"
        # Volume = 100 (bid) + 200 (ask) = 300
        assert events[0]["volume"] == "300.0"
        assert events[0]["event_type"] == "book"
        assert "2026" in events[0]["timestamp"]  # ISO format
        assert events[1]["market_id"] == "0xdef"
        assert events[1]["price"] == "0.85"

    @patch("trady_ai.adapters.polymarket.websockets.connect")
    def test_subscribe_websocket_sends_subscribe_message(self, mock_connect, adapter):
        """subscribe_websocket sends type=market subscribe with assets_ids."""
        mock_ws = _AsyncMockWS([])
        mock_connect.return_value = mock_ws

        # Consume generator (will exit when WS has no messages)
        list(adapter.subscribe_websocket(["0xabc", "0xdef"]))

        assert len(mock_ws.sent_messages) == 1
        sent = json.loads(mock_ws.sent_messages[0])
        assert sent["type"] == "market"
        assert sent["assets_ids"] == ["0xabc", "0xdef"]

    @patch("trady_ai.adapters.polymarket.websockets.connect")
    def test_subscribe_websocket_handles_connection_closed(self, mock_connect, adapter):
        """When WS closes, the generator stops gracefully (no error)."""
        mock_ws = _AsyncMockWS([])
        mock_connect.return_value = mock_ws

        events = list(adapter.subscribe_websocket(["0xabc"]))
        assert len(events) == 0


# ── Module-level helper tests ──────────────────────────────────────────────


class TestEpochMsToIso:
    """Tests for _epoch_ms_to_iso (Polymarket timestamp converter)."""

    def test_converts_string_epoch(self):
        from trady_ai.adapters.polymarket import _epoch_ms_to_iso

        result = _epoch_ms_to_iso("1784742965886")
        # 1784742965886 ms = 2026-07-22 17:56:05 UTC
        assert result.startswith("2026-07-22T17:56:05")
        assert "+00:00" in result

    def test_converts_int_epoch(self):
        from trady_ai.adapters.polymarket import _epoch_ms_to_iso

        result = _epoch_ms_to_iso(1784742965886)
        assert result.startswith("2026-07-22T17:56:05")

    def test_empty_returns_empty_string(self):
        from trady_ai.adapters.polymarket import _epoch_ms_to_iso

        assert _epoch_ms_to_iso("") == ""
        assert _epoch_ms_to_iso(None) == ""

    def test_invalid_returns_empty_string(self):
        from trady_ai.adapters.polymarket import _epoch_ms_to_iso

        assert _epoch_ms_to_iso("not-a-number") == ""
        assert _epoch_ms_to_iso("abc123") == ""


class TestNormalizeBookSnapshot:
    """Tests for _normalize_book_snapshot (Polymarket WS → event_store schema)."""

    def test_normalizes_full_snapshot(self):
        from trady_ai.adapters.polymarket import _normalize_book_snapshot

        data = {
            "market": "0xabc",
            "asset_id": "tok1",
            "timestamp": "1784742965886",
            "bids": [{"price": "0.01", "size": "100"}, {"price": "0.02", "size": "50"}],
            "asks": [{"price": "0.99", "size": "200"}],
            "last_trade_price": "0.70",
            "event_type": "book",
            "hash": "h1",
        }
        result = _normalize_book_snapshot(data)

        assert result is not None
        assert result["market_id"] == "0xabc"
        assert result["asset_id"] == "tok1"
        assert result["price"] == "0.70"
        # Volume = 100 + 50 + 200 = 350
        assert result["volume"] == "350.0"
        assert result["event_type"] == "book"
        assert result["hash"] == "h1"
        assert "2026" in result["timestamp"]

    def test_missing_required_returns_none(self):
        from trady_ai.adapters.polymarket import _normalize_book_snapshot

        # Missing market
        assert _normalize_book_snapshot({"timestamp": "123", "asset_id": "t"}) is None
        # Missing timestamp
        assert _normalize_book_snapshot({"market": "0xabc", "asset_id": "t"}) is None
        # Empty market
        assert _normalize_book_snapshot({"market": "", "timestamp": "123"}) is None

    def test_handles_empty_bids_asks(self):
        from trady_ai.adapters.polymarket import _normalize_book_snapshot

        data = {
            "market": "0xabc",
            "asset_id": "t",
            "timestamp": "1784742965886",
            "bids": [],
            "asks": [],
            "last_trade_price": "0.50",
        }
        result = _normalize_book_snapshot(data)
        assert result is not None
        assert result["volume"] == "0.0"
        assert result["price"] == "0.50"

    def test_falls_back_to_best_bid_when_no_last_trade(self):
        from trady_ai.adapters.polymarket import _normalize_book_snapshot

        data = {
            "market": "0xabc",
            "asset_id": "t",
            "timestamp": "1784742965886",
            "bids": [{"price": "0.45", "size": "100"}],
            "asks": [{"price": "0.55", "size": "100"}],
            # No last_trade_price
        }
        result = _normalize_book_snapshot(data)
        assert result is not None
        assert result["price"] == "0.45"  # best bid

    def test_handles_non_dict(self):
        from trady_ai.adapters.polymarket import _normalize_book_snapshot

        assert _normalize_book_snapshot("not a dict") is None  # type: ignore[arg-type]
        assert _normalize_book_snapshot(None) is None  # type: ignore[arg-type]
        assert _normalize_book_snapshot(123) is None  # type: ignore[arg-type]

    def test_handles_malformed_sizes_gracefully(self):
        from trady_ai.adapters.polymarket import _normalize_book_snapshot

        data = {
            "market": "0xabc",
            "asset_id": "t",
            "timestamp": "1784742965886",
            "bids": [{"price": "0.01", "size": "not-a-number"}, {"price": "0.02", "size": None}],
            "asks": [{"price": "0.99"}],  # no size key
            "last_trade_price": "0.50",
        }
        # Should not raise; just skip malformed sizes
        result = _normalize_book_snapshot(data)
        assert result is not None
        # Only valid sizes count
        assert result["volume"] == "0.0"
