"""Quote snapshots: Finnhub for the price, Yahoo Finance for what Finnhub's free plan lacks.

Finnhub's quote gives the last regular-session price, the day's range and the previous
close. Volume and pre-market or after-hours prices come from Yahoo Finance.
"""

import asyncio
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.market.market_formatter import to_float, to_int
from app.market.market_session import (
    extended_hours_status,
    get_market_session,
    has_extended_hours_activity,
    session_prices,
)
from app.schemas.market import MarketQuote

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
COMBINED_SOURCE = "Finnhub + Yahoo Finance"


def _quote_timestamp(value: int | float | None) -> datetime:
    if value is None:
        return datetime.now(UTC)

    return datetime.fromtimestamp(float(value), UTC)


def enrich_with_yahoo_market_stats(
    quote: MarketQuote, stats: dict[str, float | int | None] | None
) -> MarketQuote:
    """Fill in volume and any day figures the Finnhub quote did not include."""
    if not stats:
        return quote

    volume = quote.volume or to_int(stats.get("volume"))
    open_price = quote.open or to_float(stats.get("open"))
    high = quote.high or to_float(stats.get("high"))
    low = quote.low or to_float(stats.get("low"))
    previous_close = quote.previous_close or to_float(stats.get("previous_close"))

    if (
        volume == quote.volume
        and open_price == quote.open
        and high == quote.high
        and low == quote.low
        and previous_close == quote.previous_close
    ):
        return quote

    return quote.model_copy(
        update={
            "volume": volume,
            "open": open_price,
            "high": high,
            "low": low,
            "previous_close": previous_close,
            "source": COMBINED_SOURCE,
        }
    )


def enrich_with_yahoo_extended_hours(
    quote: MarketQuote, stats: dict[str, float | int | None] | None
) -> MarketQuote:
    """Fill in the pre-market or after-hours price when Finnhub only has the regular close.

    The change is measured against the regular session price, so an after-hours move is
    not mixed up with the day's regular move.
    """
    if (
        quote.has_extended_hours_activity
        or quote.market_session not in ("PRE_MARKET", "AFTER_HOURS")
        or not stats
    ):
        return quote

    key = "pre_market_price" if quote.market_session == "PRE_MARKET" else "post_market_price"
    extended_price = to_float(stats.get(key))
    if extended_price is None or extended_price <= 0:
        return quote

    if quote.market_session == "PRE_MARKET":
        regular_price = quote.previous_close or to_float(stats.get("previous_close"))
    else:
        regular_price = to_float(stats.get("regular_price")) or quote.regular_price

    change = extended_price - regular_price if regular_price else None
    change_percent = (
        (change / regular_price) * 100 if change is not None and regular_price else None
    )

    return quote.model_copy(
        update={
            "current_price": extended_price,
            "change": change,
            "change_percent": change_percent,
            "regular_price": regular_price,
            "extended_hours_price": extended_price,
            "has_extended_hours_activity": True,
            "extended_hours_status": "ACTIVE",
            "extended_hours_source": "Yahoo Finance",
            "source": COMBINED_SOURCE,
        }
    )


async def _fetch_yahoo_market_stats(
    symbols: list[str],
) -> dict[str, dict[str, float | int | None]]:
    from app.services.stock_service import get_stock_market_stats

    results = await asyncio.gather(
        *[get_stock_market_stats(symbol) for symbol in symbols],
        return_exceptions=True,
    )

    return {
        symbol: result
        for symbol, result in zip(symbols, results, strict=False)
        if isinstance(result, dict)
    }


async def _fetch_finnhub_quote(
    client: httpx.AsyncClient,
    symbol: str,
    api_key: str,
) -> MarketQuote | None:
    quote_response = await client.get(
        FINNHUB_QUOTE_URL,
        params={"symbol": symbol, "token": api_key},
    )
    quote_response.raise_for_status()
    payload = quote_response.json()

    current_price = to_float(payload.get("c"))
    if current_price is None or current_price <= 0:
        return None

    quote_timestamp = _quote_timestamp(payload.get("t"))
    market_session, next_market_open = get_market_session()
    previous_close = to_float(payload.get("pc"))
    extended_activity = has_extended_hours_activity(market_session, quote_timestamp)
    regular_price, extended_hours_price = session_prices(
        market_session,
        current_price,
        previous_close,
        extended_activity,
    )

    return MarketQuote(
        symbol=symbol,
        current_price=current_price,
        change=to_float(payload.get("d")),
        change_percent=to_float(payload.get("dp")),
        # Finnhub sends 0 for figures it does not have, which `or None` turns into "missing".
        high=to_float(payload.get("h")) or None,
        low=to_float(payload.get("l")) or None,
        open=to_float(payload.get("o")) or None,
        previous_close=previous_close,
        regular_price=regular_price,
        extended_hours_price=extended_hours_price,
        has_extended_hours_activity=extended_activity,
        extended_hours_status=extended_hours_status(market_session, extended_activity),
        extended_hours_source="Finnhub" if extended_activity else None,
        market_session=market_session,
        next_market_open=next_market_open,
        timestamp=quote_timestamp.isoformat(),
    )


async def get_finnhub_quotes(symbols: list[str]) -> list[MarketQuote]:
    settings = get_settings()

    if not settings.finnhub_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Finnhub API key is not configured.",
        )

    async with httpx.AsyncClient(timeout=15) as client:
        results = await asyncio.gather(
            *[_fetch_finnhub_quote(client, symbol, settings.finnhub_api_key) for symbol in symbols],
            return_exceptions=True,
        )

    quotes_by_symbol = {
        result.symbol: result for result in results if isinstance(result, MarketQuote)
    }

    yahoo_stats = await _fetch_yahoo_market_stats(list(quotes_by_symbol))
    for symbol, quote in quotes_by_symbol.items():
        stats = yahoo_stats.get(symbol)
        quote = enrich_with_yahoo_market_stats(quote, stats)
        quotes_by_symbol[symbol] = enrich_with_yahoo_extended_hours(quote, stats)

    return [quotes_by_symbol[symbol] for symbol in symbols if symbol in quotes_by_symbol]
