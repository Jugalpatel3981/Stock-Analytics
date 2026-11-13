"""Entry point for market data: cached quote snapshots and the live trade stream."""

from app.market.market_formatter import normalize_symbols
from app.market.market_scheduler import market_stats_scheduler
from app.market.rest_market_service import get_finnhub_quotes as _get_uncached_finnhub_quotes
from app.market.websocket_service import stream_finnhub_trades
from app.schemas.market import MarketQuote

__all__ = ["get_finnhub_quotes", "normalize_symbols", "stream_finnhub_trades"]


async def get_finnhub_quotes(symbols: list[str]) -> list[MarketQuote]:
    return await market_stats_scheduler.get_quotes(symbols, _get_uncached_finnhub_quotes)
