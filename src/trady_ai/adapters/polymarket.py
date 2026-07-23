"""Stateless Polymarket CLOB API adapter.

Translates Polymarket CLOB API structure into internal contracts.
All methods are pure translations — no state, no caching, no retries.

Architectural boundary: adapters translate structure, NEVER own meaning (RFC-002).
"""

import asyncio
import json
import threading
import time
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import httpx
import sqlite_utils
import structlog
import websockets

from trady_ai.core.models import MarketInput, Trade
from trady_ai.core.persistence import append_event, get_max_seq, reset_event_store

logger = structlog.get_logger()

_VALID_SIDES = frozenset({"BUY", "SELL"})
_SENTINEL: Any = object()


# ── WebSocket helpers (pure functions, no I/O) ────────────────────────────


def _epoch_ms_to_iso(epoch_ms: str | int | None) -> str:
    """Convert epoch milliseconds (Polymarket WS format) to ISO 8601 datetime.

    Pure function: same input → same output. No side effects.

    Args:
        epoch_ms: Epoch milliseconds as string or int. May be None/empty.

    Returns:
        ISO 8601 datetime string (e.g., "2026-07-22T17:42:45.886000+00:00"),
        or empty string if input is not a valid epoch.
    """
    if not epoch_ms:
        return ""
    try:
        ms = int(epoch_ms)
        return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()
    except (ValueError, TypeError, OSError, OverflowError):
        return ""


def _normalize_book_snapshot(data: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a Polymarket book snapshot to event_store schema fields.

    Polymarket WS pushes book snapshots (not individual trades/ticks). Each
    snapshot is converted to a single "tick" event with the last trade price
    and total book volume. This abstracts away the difference between tick
    streams and book snapshots so downstream code (EventCapture, strategy)
    sees a consistent interface.

    Pure function: same input → same output. No I/O, no side effects.

    Args:
        data: Dict from WS message. Required: market, asset_id, timestamp.
            Optional: bids, asks, last_trade_price, event_type, hash.

    Returns:
        Dict with: market_id, asset_id, price, volume, timestamp (ISO 8601),
            event_type, hash. None if data is malformed (missing required fields).
    """
    if not isinstance(data, dict):
        return None

    market = data.get("market", "")
    asset_id = data.get("asset_id", "")
    timestamp_ms = data.get("timestamp", "")
    if not market or not timestamp_ms:
        return None

    # Calculate book volume (sum of bid + ask sizes) for the event_store.
    bids = data.get("bids") or []
    asks = data.get("asks") or []
    book_volume = 0.0
    for b in bids:
        try:
            book_volume += float(b.get("size", 0) or 0)
        except (ValueError, TypeError):
            pass
    for a in asks:
        try:
            book_volume += float(a.get("size", 0) or 0)
        except (ValueError, TypeError):
            pass

    # Price: prefer last_trade_price (most recent executed trade), fall back
    # to best bid (most aggressive buy order in the book).
    price = str(data.get("last_trade_price") or "0")
    if price == "0" and bids:
        price = str(bids[0].get("price", "0") or "0")

    return {
        "market_id": market,
        "asset_id": asset_id,
        "price": price,
        "volume": str(book_volume),
        "timestamp": _epoch_ms_to_iso(timestamp_ms),
        "event_type": data.get("event_type", "book"),
        "hash": data.get("hash", ""),
    }


class PolymarketAdapter:
    """Stateless adapter: Polymarket CLOB API → internal contracts.

    Uses httpx directly (no SDKs). All methods are pure translations.
    No state, no caching, no retries. Fail-fast on invalid input.

    Attributes:
        _rest_url: Base URL for REST API.
        _ws_url: WebSocket endpoint URL.
        _client: Shared httpx sync client.
    """

    def __init__(
        self,
        rest_url: str,
        ws_url: str,
        api_key: str = "",
        secret: str = "",
        passphrase: str = "",
    ):
        """Initialize adapter with Polymarket API configuration.

        Args:
            rest_url: Base URL for REST API (e.g. https://clob.polymarket.com).
            ws_url: WebSocket endpoint (e.g. wss://ws-subscriptions-clob.polymarket.com/ws/market).
            api_key: Polymarket API key. Empty string in dry_run mode.
            secret: Polymarket secret key. Stored for future auth signing.
            passphrase: Polymarket passphrase. Stored for future auth signing.
        """
        self._rest_url = rest_url
        self._ws_url = ws_url
        self._secret = secret
        self._passphrase = passphrase
        headers: dict[str, str] = {}
        if api_key:
            headers["POLY-API-KEY"] = api_key
        self._client = httpx.Client(base_url=rest_url, timeout=30.0, headers=headers)

    # ── REST methods ──────────────────────────────────────────────────────────

    def get_markets(self) -> list[dict[str, Any]]:
        """GET /markets → list of available markets.

        Returns:
            list[dict]: Each dict has keys: condition_id, question, tokens, active, closed.

        Raises:
            httpx.HTTPStatusError: If API returns non-2xx.
            httpx.ConnectError: If network unreachable.
        """
        resp = self._client.get("/markets")
        resp.raise_for_status()
        return cast(list[dict[str, Any]], resp.json())

    def get_market_data(self, market_id: str) -> dict[str, Any]:
        """GET /market/{market_id} → price, volume, timestamp.

        Args:
            market_id: Polymarket condition ID (e.g. "0x123...").

        Returns:
            dict: Keys: market_id, price (str), volume (str), timestamp (ISO 8601 str),
                  best_bid (str), best_ask (str).

        Raises:
            ValueError: If market_id is empty string.
            httpx.HTTPStatusError: 404 if market not found, other non-2xx.
        """
        if not market_id:
            raise ValueError("market_id must not be empty")
        resp = self._client.get(f"/markets/{market_id}")
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    def get_order_book(self, market_id: str) -> dict[str, Any]:
        """GET /order-book?market={market_id} → bids, asks.

        Args:
            market_id: Polymarket Condition ID.

        Returns:
            dict: Keys: market_id, bids (list[dict{price: str, size: str}]),
                  asks (list[dict{price: str, size: str}]), timestamp (ISO 8601).

        Raises:
            ValueError: If market_id is empty string.
            httpx.HTTPStatusError: 404 if market not found.
        """
        if not market_id:
            raise ValueError("market_id must not be empty")
        resp = self._client.get("/order-book", params={"market": market_id})
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    def place_order(
        self, market_id: str, side: str, price: Decimal, size: Decimal
    ) -> dict[str, Any]:
        """POST /order → place GTC Limit order.

        Validates all inputs BEFORE making the HTTP call. Fail-fast.

        Args:
            market_id: Polymarket Condition ID.
            side: "BUY" or "SELL".
            price: Limit price (Decimal, > 0).
            size: Order size (Decimal, > 0).

        Returns:
            dict: Keys: order_id (str), status (str), market_id, side,
                  price (str), size (str), order_type ("GTC"), timestamp.

        Raises:
            ValueError: If side not in {"BUY", "SELL"}, price <= 0, size <= 0,
                        market_id empty.
            httpx.HTTPStatusError: If API rejects order.
        """
        if not market_id:
            raise ValueError("market_id must not be empty")
        if side not in _VALID_SIDES:
            raise ValueError("side must be BUY or SELL")
        if price <= Decimal("0"):
            raise ValueError("price must be > 0")
        if size <= Decimal("0"):
            raise ValueError("size must be > 0")

        payload = {
            "market": market_id,
            "side": side,
            "price": str(price),
            "size": str(size),
            "order_type": "GTC",
        }
        resp = self._client.post("/order", json=payload)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """DELETE /order/{order_id} → cancel pending order.

        Args:
            order_id: Order ID from place_order response.

        Returns:
            dict: Keys: order_id, status ("CANCELLED"), timestamp.

        Raises:
            ValueError: If order_id is empty string.
            httpx.HTTPStatusError: 404 if order not found.
        """
        if not order_id:
            raise ValueError("order_id must not be empty")
        resp = self._client.delete(f"/order/{order_id}")
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    def get_open_orders(self, market_id: str) -> list[dict[str, Any]]:
        """GET /orders?market={market_id}&status=OPEN → list of open orders.

        Args:
            market_id: Polymarket Condition ID.

        Returns:
            list[dict]: Each dict: order_id, market_id, side, price (str),
                        size (str), status, timestamp.

        Raises:
            httpx.HTTPStatusError: If API returns non-2xx.
        """
        resp = self._client.get(
            "/orders",
            params={"market": market_id, "status": "OPEN"},
        )
        resp.raise_for_status()
        return cast(list[dict[str, Any]], resp.json())

    # ── WebSocket ─────────────────────────────────────────────────────────────

    def subscribe_websocket(self, market_ids: list[str]) -> Generator[dict[str, Any], None, None]:
        """Connect to WS endpoint, yield parsed events.

        Creates an internal asyncio event loop to bridge the async websocket
        library into a synchronous generator. Blocks the calling thread.

        Polymarket CLOB WebSocket message format (verified 2026-07-22):

            Request:
                {"type": "market", "assets_ids": [<token_id>, ...]}

            Response (one message = one book snapshot per asset):
                [
                  {
                    "market": "0x...",           # condition_id
                    "asset_id": "526141...",     # token_id (Yes/No)
                    "timestamp": "1784742965886",  # epoch milliseconds
                    "bids": [{"price": "0.01", "size": "613"}, ...],
                    "asks": [{"price": "0.99", "size": "640.96"}, ...],
                    "tick_size": "0.01",
                    "event_type": "book",
                    "last_trade_price": "0.280",
                    "hash": "a378459a1ce1da2bbff7a675129ff480fe920825"
                  }
                ]

        The WS pushes BOOK SNAPSHOTS (not individual trades or ticks). We
        normalize each snapshot to the event_store schema (market_id, price,
        volume, timestamp, event_type) so downstream code (EventCapture,
        strategy) sees a consistent interface.

        DEVIATION: the original implementation assumed "tick"/"trade" events
        with direct price/volume fields. Polymarket's actual feed only sends
        book snapshots. The normalization layer abstracts this away.

        Args:
            market_ids: List of Polymarket token_ids (asset_ids), NOT
                condition_ids. Caller is responsible for the translation
                (see paper_trading.session._resolve_token_ids).

        Yields:
            dict: Normalized WS event with keys: market_id, asset_id, price,
                volume, timestamp (ISO 8601), event_type, hash.

        Raises:
            ValueError: If market_ids is empty.
            ConnectionError: If WS connection fails (propagated).
        """
        if not market_ids:
            raise ValueError("market_ids must not be empty")

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def _producer() -> None:
            """Connect to WS, receive messages, feed queue."""
            try:
                async with websockets.connect(self._ws_url) as ws:
                    # CORRECTED (2026-07-22): Polymarket expects type=market
                    # with assets_ids (not type=subscribe with asset_ids).
                    # Original spec assumed a different format that the
                    # CLOB WS does not implement.
                    subscribe_msg = json.dumps(
                        {"type": "market", "assets_ids": market_ids}
                    )
                    await ws.send(subscribe_msg)
                    async for message in ws:
                        data_list = json.loads(message)
                        if not isinstance(data_list, list):
                            continue
                        for data in data_list:
                            event = _normalize_book_snapshot(data)
                            if event is not None:
                                await queue.put(event)
            except websockets.ConnectionClosed:
                pass  # Generator will stop gracefully
            finally:
                await queue.put(_SENTINEL)

        # Bridge async → sync via dedicated event loop
        try:
            old_loop = asyncio.get_running_loop()
        except RuntimeError:
            old_loop = None
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(_producer())

        try:
            while True:
                event = loop.run_until_complete(queue.get())
                if event is _SENTINEL:
                    break
                yield event
        except GeneratorExit:
            # Caller stopped iterating (e.g. break or close)
            task.cancel()
            if not task.done():
                try:
                    loop.run_until_complete(task)
                except (asyncio.CancelledError, Exception):
                    pass
            raise
        finally:
            if not task.done():
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except (asyncio.CancelledError, Exception):
                    pass
            loop.close()
            if old_loop is not None:
                asyncio.set_event_loop(old_loop)

    # ── Contract mappers (pure functions) ─────────────────────────────────────

    @staticmethod
    def market_to_input(raw: dict[str, Any]) -> MarketInput:
        """Map Polymarket API response → MarketInput.

        Pure function: same input → same output. No side effects.

        Args:
            raw: Dict from get_market_data or WS event.
                 Required keys: market_id, price, volume, timestamp.

        Returns:
            MarketInput: With source='polymarket'.

        Raises:
            KeyError: If required keys missing from raw.
            ValueError: If price or volume cannot be parsed as Decimal.
        """
        return MarketInput(
            market_id=raw["market_id"],
            price=Decimal(raw["price"]),
            volume=Decimal(raw["volume"]),
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            source="polymarket",
        )

    @staticmethod
    def order_to_trade(
        raw: dict[str, Any],
        signal_id: object,
        position_id: object,
        dry_run: bool,
    ) -> Trade:
        """Map Polymarket order response → Trade.

        Pure function: same input → same output. No side effects.
        BUY side maps to action='OPEN', SELL to action='CLOSE'.

        Args:
            raw: Dict from place_order response.
                 Required keys: price, size, timestamp. Optional: side.
            signal_id: UUID of the signal that triggered this trade.
            position_id: UUID of the associated position.
            dry_run: Whether this was simulated.

        Returns:
            Trade: With auto-generated deterministic UUID.

        Raises:
            KeyError: If required keys missing.
        """
        side = raw.get("side", "BUY")
        action = "OPEN" if side == "BUY" else "CLOSE"
        return Trade(
            signal_id=signal_id,
            position_id=position_id,
            action=action,
            price=Decimal(raw["price"]),
            size=Decimal(raw["size"]),
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            dry_run=dry_run,
        )


class EventCapture:
    """Stateful capture: WS events → event_store (SQLite).

    Spawns a daemon thread that reads from PolymarketAdapter's WS generator,
    translates events via market_to_input, persists with dedup to event_store,
    and handles WS disconnect/reconnect with exponential backoff.

    State:
        _last_seq: int — last assigned sequence number.
        _db: sqlite_utils.Database
        _adapter: PolymarketAdapter
        _thread: threading.Thread | None
        _running: bool
        _error: Exception | None
    """

    def __init__(self, adapter: PolymarketAdapter, db: sqlite_utils.Database):
        self._adapter = adapter
        self._db = db
        self._last_seq = get_max_seq(db)
        self._thread: threading.Thread | None = None
        self._running = False
        self._error: Exception | None = None

    def start(self, market_ids: list[str]) -> None:
        """Start WS capture in a background daemon thread.

        Args:
            market_ids: List of Condition IDs to capture.

        Raises:
            ValueError: If market_ids is empty.
            RuntimeError: If capture is already running.
        """
        if not market_ids:
            raise ValueError("market_ids must not be empty")
        if self._running:
            raise RuntimeError("Capture is already running")
        self._running = True
        self._error = None
        self._thread = threading.Thread(
            target=self._run_loop, args=(market_ids,), daemon=True
        )
        self._thread.start()

    def _run_loop(self, market_ids: list[str]) -> None:
        """Main capture loop with reconnect and exponential backoff.

        Runs in a daemon thread. Reads from WS generator,
        captures each event, handles disconnects and retries.
        """
        retry_count = 0
        backoff = [1, 2, 4, 8, 16]
        try:
            while self._running:
                try:
                    for raw_event in self._adapter.subscribe_websocket(market_ids):
                        if not self._running:
                            break
                        self._capture_one(raw_event)
                    # WS exhausted or disconnected → reconnect
                    if self._running:
                        logger.info("ws_disconnected", market_ids=market_ids)
                        self._handle_reconnect(market_ids)
                        retry_count = 0
                except (ConnectionError, httpx.RemoteProtocolError, TimeoutError) as e:
                    if retry_count < len(backoff):
                        delay = backoff[retry_count]
                        retry_count += 1
                        logger.warning(
                            "ws_reconnect_retry",
                            attempt=retry_count,
                            delay=delay,
                            error=str(e),
                        )
                        time.sleep(delay)
                    else:
                        raise
        except Exception as e:
            logger.error("capture_thread_failed", error=str(e))
            self._error = e
            self._running = False

    def _capture_one(self, raw_event: dict[str, Any]) -> int | None:
        """Process a single raw event: translate, dedup, persist.

        Args:
            raw_event: Dict from WS or REST gap fill.

        Returns:
            int | None: Sequence number if inserted, None if duplicate.
        """
        market_input = self._adapter.market_to_input(raw_event)
        event_id = (
            f"{raw_event['market_id']}:{raw_event['timestamp']}"
            f":{raw_event.get('event_type', 'tick')}"
        )
        event_dict = {
            "event_id": event_id,
            "market_id": str(market_input.market_id),
            "price": str(market_input.price),
            "volume": str(market_input.volume),
            "timestamp": market_input.timestamp.isoformat(),
            "event_type": raw_event.get("event_type", "tick"),
            "source": "polymarket",
            "raw_payload": json.dumps(raw_event),
            "captured_at": datetime.now(UTC).isoformat(),
        }
        seq = append_event(self._db, event_dict)
        if seq is not None:
            self._last_seq = seq
        return seq

    def _handle_reconnect(self, market_ids: list[str]) -> None:
        """Handle WS disconnection with current-snapshot REST fetch.

        Polymarket CLOB API does NOT provide historical event replay
        endpoints — the closest available is /prices-history which returns
        aggregated price points (not individual events). Therefore true
        event gap-fill is NOT possible in Fase 2.

        This method fetches the CURRENT market snapshot via get_market_data()
        for each tracked market. This captures the most recent state but
        does NOT replay events that occurred during the disconnection gap.

        Fase 3+ should investigate:
        - Polymarket on-chain event indexing (contracts emit OrderFilled on Polygon)
        - /prices-history with startTs for price series reconstruction

        Known limitation: events between last captured seq and reconnect
        are lost. Documented in design deviation and spec limitation.
        """
        from trady_ai.core.persistence import get_max_seq

        max_seq = get_max_seq(self._db)
        if max_seq > 0:
            result = list(
                self._db.query(
                    "SELECT timestamp FROM event_store WHERE seq = ?", [max_seq]
                )
            )
            if result:
                for mid in market_ids:
                    try:
                        data = self._adapter.get_market_data(mid)
                        self._capture_one(data)
                    except httpx.HTTPStatusError:
                        pass  # REST endpoint may return 404, skip

    def stop(self) -> None:
        """Stop WS capture thread gracefully.

        Sets _running flag and joins thread with timeout. Idempotent.
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def reset(self) -> None:
        """DROP event_store table and recreate. DEV ONLY.

        Raises:
            RuntimeError: If environment is not 'development'.
        """
        from trady_ai.config import get_settings

        settings = get_settings()
        if settings.environment != "development":
            raise RuntimeError("reset is only available in development")
        reset_event_store(self._db)
        self._last_seq = 0
        self._error = None

    @property
    def is_running(self) -> bool:
        """Whether the capture thread is active."""
        return self._running and (
            self._thread is not None and self._thread.is_alive()
        )

    @property
    def last_seq(self) -> int:
        """Last assigned sequence number."""
        return self._last_seq

    @property
    def error(self) -> Exception | None:
        """Last unhandled exception, or None if healthy."""
        return self._error
