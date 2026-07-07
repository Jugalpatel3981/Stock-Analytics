import asyncio
from datetime import UTC, datetime
from collections.abc import Awaitable, Callable

from app.schemas.market import MarketQuote

REST_MARKET_REFRESH_SECONDS = 30


class MarketStatsScheduler:
    """Lightweight symbol-aware cache for slower Finnhub REST market statistics."""

    def __init__(self, refresh_seconds: int = REST_MARKET_REFRESH_SECONDS) -> None:
        self.refresh_seconds = refresh_seconds
        self._cache: dict[str, tuple[MarketQuote, datetime]] = {}
        self._lock = asyncio.Lock()

    def _is_fresh(self, fetched_at: datetime) -> bool:
        return (datetime.now(UTC) - fetched_at).total_seconds() < self.refresh_seconds

    async def get_quotes(
        self,
        symbols: list[str],
        fetcher: Callable[[list[str]], Awaitable[list[MarketQuote]]],
    ) -> list[MarketQuote]:
        async with self._lock:
            now = datetime.now(UTC)
            quotes_by_symbol: dict[str, MarketQuote] = {}
            stale_symbols: list[str] = []

            for symbol in symbols:
                cached = self._cache.get(symbol)
                if cached is not None:
                    quote, fetched_at = cached
                    if self._is_fresh(fetched_at):
                        quotes_by_symbol[symbol] = quote
                        continue

                stale_symbols.append(symbol)

            if stale_symbols:
                fresh_quotes = await fetcher(stale_symbols)
                fetched_at = datetime.now(UTC)
                for quote in fresh_quotes:
                    self._cache[quote.symbol] = (quote, fetched_at)
                    quotes_by_symbol[quote.symbol] = quote

            return [quotes_by_symbol[symbol] for symbol in symbols if symbol in quotes_by_symbol]


market_stats_scheduler = MarketStatsScheduler()
