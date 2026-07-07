"""Compatibility facade for market data services.

New code should import from app.market.* modules directly. Existing routes and tests keep
using this module while the market data architecture is split by responsibility.
"""

from app.market.market_formatter import normalize_symbols
from app.market.market_scheduler import market_stats_scheduler
from app.market.market_session import (
    extended_hours_status,
    get_market_session,
    has_extended_hours_activity,
    session_prices,
)
from app.market.rest_market_service import (
    enrich_with_yahoo_extended_hours as _enrich_with_yahoo_extended_hours,
    get_finnhub_quotes as _get_uncached_finnhub_quotes,
)
from app.market.websocket_service import stream_finnhub_trades
from app.schemas.market import ExtendedHoursStatus, MarketQuote, MarketSession


def _session_prices(
    market_session: MarketSession,
    current_price: float,
    previous_close: float | None,
    has_extended_hours_activity: bool,
) -> tuple[float | None, float | None]:
    return session_prices(
        market_session,
        current_price,
        previous_close,
        has_extended_hours_activity,
    )


def _extended_hours_status(
    market_session: MarketSession,
    has_extended_hours_activity: bool,
) -> ExtendedHoursStatus:
    return extended_hours_status(market_session, has_extended_hours_activity)


def _has_extended_hours_activity(*args, **kwargs) -> bool:
    return has_extended_hours_activity(*args, **kwargs)


async def get_finnhub_quotes(symbols: list[str]) -> list[MarketQuote]:
    return await market_stats_scheduler.get_quotes(symbols, _get_uncached_finnhub_quotes)
