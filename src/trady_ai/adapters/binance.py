"""Stateless Binance testnet WebSocket adapter.

Translates Binance testnet trade streams into internal MarketInput contracts.
All methods are pure translations — no state, no caching, no retries.

Architectural boundary: adapters translate structure, NEVER own meaning (RFC-002).

Ref spec: openspec/changes/binance-adapter/specs/binance-adapter/spec.md
"""
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


class BinanceAdapter:
    """Stateless adapter: Binance testnet WS → internal contracts.

    Maps Binance trade events 1:1 to MarketInput. No normalization,
    no book aggregation, no imputed volume.

    Attributes:
        _ws_url: WebSocket endpoint URL.
        _rest_url: REST API base URL (reserved for future use).
    """

    def __init__(self, ws_url: str, rest_url: str):
        """Initialize adapter with Binance API configuration.

        Args:
            ws_url: WebSocket endpoint (e.g. wss://testnet.binance.vision/ws).
            rest_url: REST API base URL (e.g. https://testnet.binance.vision).
        """
        self._ws_url = ws_url
        self._rest_url = rest_url

    # ── WebSocket ─────────────────────────────────────────────────────────────

    def subscribe_websocket(self, symbols: list[str]) -> Generator[dict[str, Any], None, None]:
        """Connect to Binance WS endpoint, subscribe to trade streams, yield parsed events.

        Creates an internal asyncio event loop to bridge the async websocket
        library into a synchronous generator. Blocks the calling thread.

        Binance combined stream format (websocket streams API):
            Request:
                {"method": "SUBSCRIBE", "params": ["btcusdt@trade", ...], "id": 1}
            Response (each message = one trade event):
                {"e": "trade", "E": 1752000000000, "s": "BTCUSDT",
                 "p": "98765.43", "q": "0.00123", ...}

        Args:
            symbols: List of lowercase trading pair symbols (e.g. ["btcusdt", "ethusdt"]).

        Yields:
            dict: Parsed trade event from Binance WS.

        Raises:
            ValueError: If symbols is empty.
            ConnectionError: If WS connection fails (propagated).
        """
        if not symbols:
            raise ValueError("symbols must not be empty")

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def _producer() -> None:
            """Connect to WS, subscribe, read messages, feed queue."""
            try:
                streams = "/".join(f"{s.lower()}@trade" for s in symbols)
                url = f"{self._ws_url}/stream?streams={streams}"
                async with websockets.connect(url) as ws:
                    async for message in ws:
                        try:
                            raw = json.loads(message)
                        except (json.JSONDecodeError, ValueError):
                            logger.warning("non_json_message_skipped", raw=message[:200])
                            continue
                        # Binance combined streams wrap events in {"stream": ..., "data": {...}}
                        data = raw.get("data", raw) if isinstance(raw, dict) else raw
                        if isinstance(data, dict):
                            await queue.put(data)
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
        """Map Binance trade event → MarketInput.

        Pure function: same input → same output. No side effects.

        Field mapping (Binance → MarketInput):
            E (int epoch ms) → timestamp
            s (str)          → market_id (lowercased)
            p (str)          → price (Decimal)
            q (str)          → volume (Decimal)
            (static)         → source="binance"

        Args:
            raw: Dict from Binance WS trade event.
                 Required keys: E, s, p, q.

        Returns:
            MarketInput: With source='binance'.

        Raises:
            KeyError: If required keys missing from raw.
            ValueError: If price or volume cannot be parsed as Decimal.
        """
        return MarketInput(
            timestamp=datetime.fromtimestamp(raw["E"] / 1000, tz=UTC),
            market_id=raw["s"].lower(),
            price=Decimal(raw["p"]),
            volume=Decimal(raw["q"]),
            source="binance",
        )
