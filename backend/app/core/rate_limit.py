"""In-memory sliding-window rate limiting, used as a FastAPI dependency.

State lives in the process, which suits a single backend instance. A multi-instance
deployment would move this to Redis.
"""

import math
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_registry: list["RateLimit"] = []


class RateLimit:
    def __init__(self, name: str, max_requests: int, window_seconds: float) -> None:
        self.name = name
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)
        _registry.append(self)

    def check(self, key: str) -> float | None:
        """Record a hit for `key`. Returns seconds to wait if the limit is exceeded."""
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return hits[0] + self.window_seconds - now

        hits.append(now)
        return None

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        retry_after = self.check(client_ip)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
            )

    def reset(self) -> None:
        self._hits.clear()


def reset_all_rate_limits() -> None:
    for limit in _registry:
        limit.reset()


login_rate_limit = RateLimit("login", max_requests=10, window_seconds=60)
register_rate_limit = RateLimit("register", max_requests=5, window_seconds=60)
demo_rate_limit = RateLimit("demo", max_requests=20, window_seconds=60)
chat_rate_limit = RateLimit("chat", max_requests=15, window_seconds=60)
