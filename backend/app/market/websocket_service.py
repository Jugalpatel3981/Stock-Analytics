"""Streams live trades to one browser through the shared Finnhub connection."""

import asyncio
import contextlib
from datetime import UTC, datetime

from fastapi import WebSocket

from app.core.config import get_settings
from app.market.stream_hub import StreamClient, finnhub_stream_hub


async def _forward_trades(client: StreamClient, websocket: WebSocket) -> None:
    while True:
        message = await client.queue.get()
        await websocket.send_json(message)


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


async def stream_finnhub_trades(websocket: WebSocket, symbols: list[str]) -> None:
    await websocket.accept()

    if not get_settings().finnhub_api_key:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Finnhub API key is not configured.",
                "symbols": symbols,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        await websocket.close()
        return

    client = await finnhub_stream_hub.register(symbols)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "symbols": sorted(client.symbols),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Stop as soon as either the browser leaves or sending to it fails.
        tasks = {
            asyncio.create_task(_forward_trades(client, websocket)),
            asyncio.create_task(_wait_for_disconnect(websocket)),
        }
        _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
    finally:
        await finnhub_stream_hub.unregister(client)
