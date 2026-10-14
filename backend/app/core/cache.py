"""Small in-process TTL cache for slow upstream calls such as Yahoo Finance."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable
from typing import Any, TypeVar

T = TypeVar("T")

_registry: list[TTLCache] = []


class TTLCache:
    def __init__(self, ttl_seconds: float, max_entries: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        _registry.append(self)

    def get(self, key: Hashable) -> tuple[bool, Any]:
        entry = self._entries.get(key)
        if entry is None:
            return False, None

        expires_at, value = entry
        if expires_at < time.monotonic():
            del self._entries[key]
            return False, None

        self._entries.move_to_end(key)
        return True, value

    def set(self, key: Hashable, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        self._entries[key] = (time.monotonic() + ttl, value)
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    async def get_or_set(
        self,
        key: Hashable,
        factory: Callable[[], Awaitable[T]],
        ttl_seconds: float | None = None,
    ) -> T:
        """Return the cached value, or await `factory` and cache its result.

        Exceptions are not cached, so a failed upstream call is retried next time.
        """
        found, value = self.get(key)
        if found:
            return value

        value = await factory()
        self.set(key, value, ttl_seconds)
        return value

    def clear(self) -> None:
        self._entries.clear()


def clear_all_caches() -> None:
    for cache in _registry:
        cache.clear()
