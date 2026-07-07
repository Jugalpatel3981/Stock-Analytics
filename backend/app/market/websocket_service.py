import json
from datetime import UTC, datetime

import websockets
from fastapi import WebSocket

from app.core.config import get_settings


def timestamp_from_epoch_ms(value: int | float | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()

    return datetime.fromtimestamp(float(value) / 1000, UTC).isoformat()


async def stream_finnhub_trades(websocket: WebSocket, symbols: list[str]) -> None:
    settings = get_settings()
    await websocket.accept()

    if not settings.finnhub_api_key:
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

    url = f"wss://ws.finnhub.io?token={settings.finnhub_api_key}"
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as finnhub_socket:
        subscribed_symbols: set[str] = set()
        for symbol in symbols:
            if symbol not in subscribed_symbols:
                await finnhub_socket.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                subscribed_symbols.add(symbol)

        await websocket.send_json(
            {
                "type": "connected",
                "symbols": sorted(subscribed_symbols),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        async for raw_message in finnhub_socket:
            payload = json.loads(raw_message)

            if payload.get("type") != "trade":
                continue

            for trade in payload.get("data", []):
                await websocket.send_json(
                    {
                        "type": "trade",
                        "symbol": trade.get("s"),
                        "price": trade.get("p"),
                        "timestamp": timestamp_from_epoch_ms(trade.get("t")),
                        "source": "Finnhub",
                    }
                )
