"""Stateless Bybit testnet WebSocket adapter.

Translates Bybit testnet trade streams into internal MarketInput contracts.
All methods are pure translations — no state, no caching, no retries.

Architectural boundary: adapters translate structure, NEVER own meaning (RFC-002).

Key differences from BinanceAdapter:
  - Bybit uses JSON subscribe ("op": "subscribe", "args": ["publicTrade.<SYMBOL>"])
  - Trades arrive in data[] arrays — adapter yields each individually
  - Field keys: T→timestamp, s→market_id (uppercase), p→price, v→volume

Ref spec: openspec/changes/bybit-adapter/specs/bybit-adapter/spec.md
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
import websockets

from trady_ai.core.models import MarketInput

logger = structlog.get_logger()

_SENTINEL: Any = object()


class BybitAdapter:
    """Stateless adapter: Bybit testnet WS → internal contracts.

    Maps Bybit trade events 1:1 to MarketInput. No normalization,
    no book aggregation, no imputed volume.

    Attributes:
        _ws_url: WebSocket endpoint URL.
        _rest_url: REST API base URL (reserved for future use).
    """

    def __init__(self, ws_url: str, rest_url: str):
        """Initialize adapter with Bybit API configuration.

        Args:
            ws_url: WebSocket endpoint (e.g. wss://stream-testnet.bybit.com/v5/public/spot).
            rest_url: REST API base URL (e.g. https://api-testnet.bybit.com).
        """
        self._ws_url = ws_url
        self._rest_url = rest_url

    # ── WebSocket ─────────────────────────────────────────────────────────────

    def subscribe_websocket(self, symbols: list[str]) -> Generator[dict[str, Any], None, None]:
        """Connect to Bybit WS endpoint, subscribe to trade streams, yield parsed events.

        Creates an internal asyncio event loop to bridge the async websocket
        library into a synchronous generator. Blocks the calling thread.

        Bybit subscription format (JSON):
            Request:
                {"op": "subscribe", "args": ["publicTrade.BTCUSDT", ...]}
            Response (each message = batch of trade events in data[]):
                {"topic": "publicTrade.BTCUSDT", "type": "snapshot",
                 "data": [{"T": 1752000000000, "s": "BTCUSDT",
                           "p": "98765.43", "v": "0.00123"}, ...]}

        Args:
            symbols: List of UPPERCASE trading pair symbols (e.g. ["BTCUSDT", "ETHUSDT"]).

        Yields:
            dict: Individual trade event from Bybit data[] array.

        Raises:
            ValueError: If symbols is empty.
            ConnectionError: If WS connection fails (propagated).
        """
        if not symbols:
            raise ValueError("symbols must not be empty")

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def _producer() -> None:
            """Connect to WS, subscribe, read messages, iterate data[], feed queue."""
            try:
                async with websockets.connect(self._ws_url) as ws:
                    # Subscribe to all symbols
                    args = [f"publicTrade.{s}" for s in symbols]
                    subscribe_msg = json.dumps({"op": "subscribe", "args": args})
                    await ws.send(subscribe_msg)

                    async for message in ws:
                        try:
                            raw = json.loads(message)
                        except (json.JSONDecodeError, ValueError):
                            logger.warning("non_json_message_skipped", raw=message[:200])
                            continue

                        # Bybit wraps trades in data[] arrays — yield each individually
                        if isinstance(raw, dict):
                            data = raw.get("data", [])
                            if isinstance(data, list):
                                for trade in data:
                                    if isinstance(trade, dict):
                                        await queue.put(trade)
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
        """Map Bybit trade event → MarketInput.

        Pure function: same input → same output. No side effects.

        Field mapping (Bybit → MarketInput):
            T (int epoch ms) → timestamp
            s (str)          → market_id (uppercased)
            p (str)          → price (Decimal)
            v (str)          → volume (Decimal)
            (static)         → source="bybit"

        Args:
            raw: Dict from Bybit WS trade event.
                 Required keys: T, s, p, v.

        Returns:
            MarketInput: With source='bybit'.

        Raises:
            KeyError: If required keys missing from raw.
            ValueError: If price or volume cannot be parsed as Decimal.
        """
        return MarketInput(
            timestamp=datetime.fromtimestamp(raw["T"] / 1000, tz=UTC),
            market_id=raw["s"].upper(),
            price=Decimal(raw["p"]),
            volume=Decimal(raw["v"]),
            source="bybit",
        )
