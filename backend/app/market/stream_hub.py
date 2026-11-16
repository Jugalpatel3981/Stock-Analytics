"""One shared live connection to Finnhub, fanned out to every browser that is listening.

Finnhub's free plan allows a single WebSocket connection per API key: opening a second one
closes the first. Instead of one Finnhub connection per browser tab, the backend keeps one
connection, subscribes to the union of the symbols that browsers want, and passes each trade
to the browsers that asked for that symbol. If Finnhub drops the connection, the hub
reconnects with a growing delay and subscribes again.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import count
from typing import Any

import websockets

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FINNHUB_STREAM_URL = "wss://ws.finnhub.io"
# Seconds to wait before each reconnection attempt; the last value repeats.
RECONNECT_DELAYS = (1, 2, 5, 10, 30)
# Keep the connection open briefly after the last browser leaves, so moving between pages
# does not close and reopen it.
IDLE_CLOSE_SECONDS = 15
# Trades waiting to be sent to one slow browser. Beyond this the oldest are dropped.
CLIENT_QUEUE_SIZE = 500

Connector = Callable[[str], Any]


def _default_connector(url: str) -> Any:
    return websockets.connect(url, ping_interval=20, ping_timeout=20)


def _timestamp_from_epoch_ms(value: int | float | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()

    return datetime.fromtimestamp(float(value) / 1000, UTC).isoformat()


@dataclass(eq=False)
class StreamClient:
    """One browser connection: the symbols it wants and the trades waiting to be sent."""

    id: int
    symbols: frozenset[str]
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=CLIENT_QUEUE_SIZE)
    )

    def push(self, message: dict[str, Any]) -> None:
        if self.queue.full():
            # A slow browser should get the latest prices, not an ever-growing backlog.
            self.queue.get_nowait()
        self.queue.put_nowait(message)


class FinnhubStreamHub:
    def __init__(
        self,
        connector: Connector = _default_connector,
        reconnect_delays: tuple[float, ...] = RECONNECT_DELAYS,
        idle_close_seconds: float = IDLE_CLOSE_SECONDS,
    ) -> None:
        self._connector = connector
        self._reconnect_delays = reconnect_delays
        self._idle_close_seconds = idle_close_seconds
        self._clients: dict[int, StreamClient] = {}
        self._ids = count(1)
        self._socket: Any | None = None
        self._subscribed: set[str] = set()
        self._run_task: asyncio.Task[None] | None = None
        self._idle_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self.connection_count = 0

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    @property
    def subscribed_symbols(self) -> frozenset[str]:
        return frozenset(self._subscribed)

    def _wanted_symbols(self) -> set[str]:
        return {symbol for client in self._clients.values() for symbol in client.symbols}

    async def register(self, symbols: list[str]) -> StreamClient:
        client = StreamClient(id=next(self._ids), symbols=frozenset(symbols))
        self._clients[client.id] = client

        if self._idle_task is not None:
            self._idle_task.cancel()
            self._idle_task = None

        if self._run_task is None or self._run_task.done():
            self._run_task = asyncio.create_task(self._run())
        else:
            await self._sync_subscriptions()

        return client

    async def unregister(self, client: StreamClient) -> None:
        if self._clients.pop(client.id, None) is None:
            return

        if self._clients:
            await self._sync_subscriptions()
        elif self._idle_task is None:
            self._idle_task = asyncio.create_task(self._close_when_idle())

    async def close(self) -> None:
        """Stop streaming. Used when the application shuts down."""
        self._clients.clear()
        for task in (self._idle_task, self._run_task):
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        self._idle_task = None
        self._run_task = None

    async def _close_when_idle(self) -> None:
        await asyncio.sleep(self._idle_close_seconds)
        self._idle_task = None
        if self._clients or self._run_task is None:
            return

        self._run_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await self._run_task
        self._run_task = None

    async def _sync_subscriptions(self) -> None:
        async with self._send_lock:
            socket = self._socket
            if socket is None:
                return

            wanted = self._wanted_symbols()
            try:
                for symbol in sorted(wanted - self._subscribed):
                    await socket.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                    self._subscribed.add(symbol)
                for symbol in sorted(self._subscribed - wanted):
                    await socket.send(json.dumps({"type": "unsubscribe", "symbol": symbol}))
                    self._subscribed.discard(symbol)
            except Exception as exc:  # the reader loop notices the closed socket and reconnects
                logger.warning("Could not update Finnhub subscriptions: %s", exc)

    def _dispatch(self, raw_message: str | bytes) -> None:
        try:
            payload = json.loads(raw_message)
        except (TypeError, ValueError):
            return

        if payload.get("type") == "error":
            logger.warning("Finnhub stream error: %s", payload.get("msg"))
            return

        if payload.get("type") != "trade":
            return

        for trade in payload.get("data") or []:
            symbol = trade.get("s")
            message = {
                "type": "trade",
                "symbol": symbol,
                "price": trade.get("p"),
                "timestamp": _timestamp_from_epoch_ms(trade.get("t")),
                "source": "Finnhub",
            }
            for client in self._clients.values():
                if symbol in client.symbols:
                    client.push(message)

    async def _run(self) -> None:
        attempt = 0
        while self._clients:
            api_key = get_settings().finnhub_api_key
            try:
                async with self._connector(f"{FINNHUB_STREAM_URL}?token={api_key}") as socket:
                    self._socket = socket
                    self._subscribed = set()
                    self.connection_count += 1
                    await self._sync_subscriptions()
                    attempt = 0
                    async for raw_message in socket:
                        self._dispatch(raw_message)
                logger.info("Finnhub stream closed; reconnecting")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Finnhub stream disconnected (%s); reconnecting", exc)
            finally:
                self._socket = None
                self._subscribed = set()

            if not self._clients:
                break

            delay = self._reconnect_delays[min(attempt, len(self._reconnect_delays) - 1)]
            attempt += 1
            await asyncio.sleep(delay)


finnhub_stream_hub = FinnhubStreamHub()
