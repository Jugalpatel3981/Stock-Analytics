import pytest

from app.core import cache as cache_module
from app.core.cache import TTLCache


async def test_get_or_set_reuses_value_until_expiry(monkeypatch) -> None:
    now = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: now[0])
    calls = []

    async def factory() -> str:
        calls.append(1)
        return f"value-{len(calls)}"

    cache = TTLCache(ttl_seconds=10)

    assert await cache.get_or_set("key", factory) == "value-1"
    assert await cache.get_or_set("key", factory) == "value-1"
    now[0] += 11
    assert await cache.get_or_set("key", factory) == "value-2"


async def test_failures_are_not_cached() -> None:
    cache = TTLCache(ttl_seconds=10)

    async def failing() -> str:
        raise RuntimeError("upstream down")

    async def working() -> str:
        return "ok"

    with pytest.raises(RuntimeError):
        await cache.get_or_set("key", failing)
    assert await cache.get_or_set("key", working) == "ok"


def test_oldest_entries_are_evicted() -> None:
    cache = TTLCache(ttl_seconds=10, max_entries=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    assert cache.get("a") == (False, None)
    assert cache.get("c") == (True, 3)
