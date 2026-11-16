import asyncio
import json

import pytest

from app.core.config import get_settings
from app.market.stream_hub import CLIENT_QUEUE_SIZE, FinnhubStreamHub, StreamClient

DROP = object()


class FakeSocket:
    """Stands in for a Finnhub WebSocket: records what is sent and replays queued messages."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.sent: list[dict] = []
        self.closed = False
        self._incoming: asyncio.Queue = asyncio.Queue()

    async def __aenter__(self) -> "FakeSocket":
        return self

    async def __aexit__(self, *_exc) -> None:
        self.closed = True

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    def __aiter__(self) -> "FakeSocket":
        return self

    async def __anext__(self) -> str:
        item = await self._incoming.get()
        if item is DROP:
            raise ConnectionError("Finnhub closed the connection")
        return item

    def trade(self, symbol: str, price: float) -> None:
        payload = {"type": "trade", "data": [{"s": symbol, "p": price, "t": 1794858367620}]}
        self._incoming.put_nowait(json.dumps(payload))

    def raw(self, message: str) -> None:
        self._incoming.put_nowait(message)

    def drop(self) -> None:
        self._incoming.put_nowait(DROP)

    def subscriptions(self) -> set[str]:
        symbols: set[str] = set()
        for message in self.sent:
            if message["type"] == "subscribe":
                symbols.add(message["symbol"])
            elif message["type"] == "unsubscribe":
                symbols.discard(message["symbol"])
        return symbols


class FakeFinnhub:
    def __init__(self) -> None:
        self.sockets: list[FakeSocket] = []

    def __call__(self, url: str) -> FakeSocket:
        socket = FakeSocket(url)
        self.sockets.append(socket)
        return socket


async def settle() -> None:
    """Let the hub's background task run until it is waiting again."""
    for _ in range(20):
        await asyncio.sleep(0)


def received(client: StreamClient) -> list[tuple[str, float]]:
    messages = []
    while not client.queue.empty():
        message = client.queue.get_nowait()
        messages.append((message["symbol"], message["price"]))
    return messages


@pytest.fixture
def finnhub(monkeypatch) -> FakeFinnhub:
    monkeypatch.setattr(get_settings(), "finnhub_api_key", "test-key")
    return FakeFinnhub()


@pytest.fixture
async def hub(finnhub):
    stream_hub = FinnhubStreamHub(connector=finnhub, reconnect_delays=(0,), idle_close_seconds=0)
    yield stream_hub
    await stream_hub.close()


async def test_browsers_share_one_finnhub_connection(hub, finnhub) -> None:
    first = await hub.register(["AAPL", "NVDA"])
    second = await hub.register(["NVDA", "TSLA"])
    await settle()

    assert len(finnhub.sockets) == 1
    assert finnhub.sockets[0].url.endswith("token=test-key")
    assert finnhub.sockets[0].subscriptions() == {"AAPL", "NVDA", "TSLA"}

    finnhub.sockets[0].trade("NVDA", 155.5)
    finnhub.sockets[0].trade("AAPL", 351.0)
    finnhub.sockets[0].trade("TSLA", 375.0)
    await settle()

    assert received(first) == [("NVDA", 155.5), ("AAPL", 351.0)]
    assert received(second) == [("NVDA", 155.5), ("TSLA", 375.0)]


async def test_symbols_nobody_wants_are_unsubscribed(hub, finnhub) -> None:
    first = await hub.register(["AAPL", "NVDA"])
    second = await hub.register(["NVDA", "TSLA"])
    await settle()

    await hub.unregister(second)

    assert finnhub.sockets[0].subscriptions() == {"AAPL", "NVDA"}
    assert {"type": "unsubscribe", "symbol": "TSLA"} in finnhub.sockets[0].sent
    assert {"type": "unsubscribe", "symbol": "NVDA"} not in finnhub.sockets[0].sent
    assert hub.is_connected
    await hub.unregister(first)


async def test_reconnects_and_resubscribes_after_finnhub_drops_the_connection(hub, finnhub) -> None:
    client = await hub.register(["AAPL", "MSFT"])
    await settle()

    finnhub.sockets[0].drop()
    await settle()

    assert len(finnhub.sockets) == 2
    assert finnhub.sockets[1].subscriptions() == {"AAPL", "MSFT"}
    assert hub.connection_count == 2

    finnhub.sockets[1].trade("MSFT", 517.9)
    await settle()
    assert received(client) == [("MSFT", 517.9)]


async def test_connection_closes_after_the_last_browser_leaves(hub, finnhub) -> None:
    client = await hub.register(["AAPL"])
    await settle()

    await hub.unregister(client)
    await asyncio.sleep(0.05)

    assert finnhub.sockets[0].closed
    assert not hub.is_connected

    await hub.register(["NVDA"])
    await settle()
    assert len(finnhub.sockets) == 2
    assert finnhub.sockets[1].subscriptions() == {"NVDA"}


async def test_a_new_browser_during_the_idle_period_keeps_the_connection(finnhub) -> None:
    hub = FinnhubStreamHub(connector=finnhub, reconnect_delays=(0,), idle_close_seconds=0.2)
    first = await hub.register(["AAPL"])
    await settle()

    await hub.unregister(first)
    await hub.register(["AAPL"])
    await asyncio.sleep(0.3)

    assert len(finnhub.sockets) == 1
    assert not finnhub.sockets[0].closed
    await hub.close()


async def test_other_finnhub_messages_are_ignored(hub, finnhub) -> None:
    client = await hub.register(["AAPL"])
    await settle()

    finnhub.sockets[0].raw('{"type": "ping"}')
    finnhub.sockets[0].raw('{"type": "error", "msg": "Subscribing to too many symbols"}')
    finnhub.sockets[0].raw("not json")
    finnhub.sockets[0].trade("AAPL", 351.0)
    await settle()

    assert received(client) == [("AAPL", 351.0)]
    assert hub.is_connected


def test_a_slow_browser_keeps_the_newest_trades() -> None:
    client = StreamClient(id=1, symbols=frozenset({"AAPL"}))

    for price in range(CLIENT_QUEUE_SIZE + 3):
        client.push({"symbol": "AAPL", "price": price})

    assert client.queue.qsize() == CLIENT_QUEUE_SIZE
    assert client.queue.get_nowait()["price"] == 3
