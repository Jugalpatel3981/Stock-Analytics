import asyncio
from datetime import UTC, datetime, time
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.market.market_formatter import to_float, to_int
from app.market.market_session import (
    MARKET_TIMEZONE,
    extended_hours_status,
    get_market_session,
    has_extended_hours_activity,
    session_prices,
)
from app.schemas.market import MarketQuote, MarketSession

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
FINNHUB_CANDLE_URL = "https://finnhub.io/api/v1/stock/candle"
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"


def _timestamp_from_epoch_seconds(value: int | float | None) -> str | None:
    if value is None:
        return None

    return datetime.fromtimestamp(float(value), UTC).isoformat()


def _quote_timestamp(value: int | float | None) -> datetime:
    if value is None:
        return datetime.now(UTC)

    return datetime.fromtimestamp(float(value), UTC)


def _current_market_day_epoch_range() -> tuple[int, int]:
    eastern_now = datetime.now(UTC).astimezone(MARKET_TIMEZONE)
    eastern_start = datetime.combine(eastern_now.date(), time(0, 0), tzinfo=MARKET_TIMEZONE)
    return int(eastern_start.timestamp()), int(eastern_now.timestamp())


def _candle_values(payload: dict[str, Any], key: str) -> list[Any]:
    values = payload.get(key)
    if not isinstance(values, list):
        return []

    return values


def _stats_from_candle_payload(payload: dict[str, Any]) -> dict[str, float | int | None]:
    if payload.get("s") != "ok":
        return {}

    opens = [value for value in (to_float(item) for item in _candle_values(payload, "o")) if value is not None]
    highs = [value for value in (to_float(item) for item in _candle_values(payload, "h")) if value is not None]
    lows = [value for value in (to_float(item) for item in _candle_values(payload, "l")) if value is not None]
    volumes = [value for value in (to_int(item) for item in _candle_values(payload, "v")) if value is not None]

    return {
        "open": opens[0] if opens else None,
        "high": max(highs) if highs else None,
        "low": min(lows) if lows else None,
        "volume": sum(volumes) if volumes else None,
    }


def _quote_from_yahoo_payload(payload: dict[str, Any], market_session: MarketSession) -> dict[str, float | str | None] | None:
    if market_session == "PRE_MARKET":
        price = to_float(payload.get("preMarketPrice"))
        change = to_float(payload.get("preMarketChange"))
        change_percent = to_float(payload.get("preMarketChangePercent"))
        timestamp = _timestamp_from_epoch_seconds(payload.get("preMarketTime"))
        regular_price = (
            to_float(payload.get("regularMarketPreviousClose"))
            or to_float(payload.get("regularMarketPrice"))
            or to_float(payload.get("previousClose"))
        )
    elif market_session == "AFTER_HOURS":
        price = to_float(payload.get("postMarketPrice"))
        change = to_float(payload.get("postMarketChange"))
        change_percent = to_float(payload.get("postMarketChangePercent"))
        timestamp = _timestamp_from_epoch_seconds(payload.get("postMarketTime"))
        regular_price = (
            to_float(payload.get("regularMarketPrice"))
            or to_float(payload.get("regularMarketPreviousClose"))
            or to_float(payload.get("previousClose"))
        )
    else:
        return None

    if price is None or price <= 0:
        return None

    if change is None and regular_price:
        change = price - regular_price

    if change_percent is None and regular_price:
        change_percent = ((change or 0) / regular_price) * 100

    return {
        "price": price,
        "change": change,
        "change_percent": change_percent,
        "regular_price": regular_price,
        "timestamp": timestamp,
    }


def enrich_with_yahoo_market_stats(quote: MarketQuote, yahoo_payload: dict[str, Any] | None) -> MarketQuote:
    if yahoo_payload is None:
        return quote

    volume = quote.volume or to_int(yahoo_payload.get("regularMarketVolume"))
    open_price = quote.open or to_float(yahoo_payload.get("regularMarketOpen"))
    high = quote.high or to_float(yahoo_payload.get("regularMarketDayHigh"))
    low = quote.low or to_float(yahoo_payload.get("regularMarketDayLow"))
    previous_close = quote.previous_close or to_float(yahoo_payload.get("regularMarketPreviousClose"))

    if volume == quote.volume and open_price == quote.open and high == quote.high and low == quote.low and previous_close == quote.previous_close:
        return quote

    return quote.model_copy(
        update={
            "volume": volume,
            "open": open_price,
            "high": high,
            "low": low,
            "previous_close": previous_close,
            "source": "Finnhub + Yahoo Finance",
        }
    )

def enrich_with_yfinance_market_stats(quote: MarketQuote, stats: dict[str, float | int | None] | None) -> MarketQuote:
    if not stats:
        return quote

    volume = quote.volume or to_int(stats.get("volume"))
    open_price = quote.open or to_float(stats.get("open"))
    high = quote.high or to_float(stats.get("high"))
    low = quote.low or to_float(stats.get("low"))
    previous_close = quote.previous_close or to_float(stats.get("previous_close"))

    if volume == quote.volume and open_price == quote.open and high == quote.high and low == quote.low and previous_close == quote.previous_close:
        return quote

    return quote.model_copy(
        update={
            "volume": volume,
            "open": open_price,
            "high": high,
            "low": low,
            "previous_close": previous_close,
            "source": "Finnhub + yfinance",
        }
    )


async def _fetch_yfinance_market_stats(symbols: list[str]) -> dict[str, dict[str, float | int | None]]:
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

def enrich_with_yahoo_extended_hours(quote: MarketQuote, yahoo_payload: dict[str, Any] | None) -> MarketQuote:
    if quote.has_extended_hours_activity or quote.market_session not in ("PRE_MARKET", "AFTER_HOURS") or yahoo_payload is None:
        return quote

    yahoo_quote = _quote_from_yahoo_payload(yahoo_payload, quote.market_session)
    if yahoo_quote is None:
        return quote.model_copy(
            update={
                "extended_hours_status": extended_hours_status(
                    quote.market_session,
                    quote.has_extended_hours_activity,
                ),
            }
        )

    regular_price = to_float(yahoo_quote.get("regular_price")) or quote.regular_price or quote.previous_close

    return quote.model_copy(
        update={
            "current_price": yahoo_quote["price"],
            "change": yahoo_quote["change"],
            "change_percent": yahoo_quote["change_percent"],
            "regular_price": regular_price,
            "extended_hours_price": yahoo_quote["price"],
            "has_extended_hours_activity": True,
            "extended_hours_status": "ACTIVE",
            "extended_hours_source": "Yahoo Finance",
            "timestamp": yahoo_quote["timestamp"] or quote.timestamp,
            "source": "Finnhub + Yahoo Finance",
        }
    )


async def _fetch_yahoo_extended_quotes(
    client: httpx.AsyncClient,
    symbols: list[str],
) -> dict[str, dict[str, Any]]:
    if not symbols:
        return {}

    response = await client.get(
        YAHOO_QUOTE_URL,
        params={
            "symbols": ",".join(symbols),
            "fields": ",".join(
                [
                    "symbol",
                    "regularMarketPrice",
                    "regularMarketPreviousClose",
                    "regularMarketVolume",
                    "regularMarketOpen",
                    "regularMarketDayHigh",
                    "regularMarketDayLow",
                    "preMarketPrice",
                    "preMarketChange",
                    "preMarketChangePercent",
                    "preMarketTime",
                    "postMarketPrice",
                    "postMarketChange",
                    "postMarketChangePercent",
                    "postMarketTime",
                ]
            ),
        },
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("quoteResponse", {}).get("result", [])

    return {
        str(item.get("symbol", "")).upper(): item
        for item in results
        if item.get("symbol")
    }


async def _fetch_finnhub_candle_stats(
    client: httpx.AsyncClient,
    symbol: str,
    api_key: str,
    resolution: str,
) -> dict[str, float | int | None]:
    start_epoch, end_epoch = _current_market_day_epoch_range()
    response = await client.get(
        FINNHUB_CANDLE_URL,
        params={
            "symbol": symbol,
            "resolution": resolution,
            "from": start_epoch,
            "to": end_epoch,
            "token": api_key,
        },
    )
    response.raise_for_status()
    return _stats_from_candle_payload(response.json())


async def _fetch_finnhub_daily_stats(
    client: httpx.AsyncClient,
    symbol: str,
    api_key: str,
) -> dict[str, float | int | None]:
    for resolution in ("5", "1", "D"):
        stats = await _fetch_finnhub_candle_stats(client, symbol, api_key, resolution)
        if stats.get("volume"):
            return stats

    return {}


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

    daily_stats: dict[str, float | int | None] = {}
    try:
        daily_stats = await _fetch_finnhub_daily_stats(client, symbol, api_key)
    except Exception:
        daily_stats = {}

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
        high=to_float(daily_stats.get("high")) or to_float(payload.get("h")),
        low=to_float(daily_stats.get("low")) or to_float(payload.get("l")),
        open=to_float(daily_stats.get("open")) or to_float(payload.get("o")),
        previous_close=previous_close,
        volume=to_int(daily_stats.get("volume")),
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
            *[
                _fetch_finnhub_quote(client, symbol, settings.finnhub_api_key)
                for symbol in symbols
            ],
            return_exceptions=True,
        )

        quotes_by_symbol = {
            result.symbol: result
            for result in results
            if isinstance(result, MarketQuote)
        }

        market_session, _next_market_open = get_market_session()
        symbols_needing_extended_fallback = [
            symbol
            for symbol, quote in quotes_by_symbol.items()
            if market_session in ("PRE_MARKET", "AFTER_HOURS") and not quote.has_extended_hours_activity
        ]
        symbols_needing_market_stats_fallback = [
            symbol
            for symbol, quote in quotes_by_symbol.items()
            if quote.volume is None or quote.open is None or quote.high is None or quote.low is None
        ]
        yahoo_symbols = sorted(set(symbols_needing_extended_fallback + symbols_needing_market_stats_fallback))
        yahoo_quotes: dict[str, dict[str, Any]] = {}
        if yahoo_symbols:
            try:
                yahoo_quotes = await _fetch_yahoo_extended_quotes(client, yahoo_symbols)
            except Exception:
                yahoo_quotes = {}

        for symbol in yahoo_symbols:
            quote = quotes_by_symbol.get(symbol)
            if quote is not None:
                quotes_by_symbol[symbol] = enrich_with_yahoo_market_stats(quote, yahoo_quotes.get(symbol))

        symbols_needing_yfinance_fallback = [
            symbol
            for symbol, quote in quotes_by_symbol.items()
            if quote.volume is None or quote.open is None or quote.high is None or quote.low is None
        ]
        if symbols_needing_yfinance_fallback:
            yfinance_stats = await _fetch_yfinance_market_stats(symbols_needing_yfinance_fallback)
            for symbol in symbols_needing_yfinance_fallback:
                quote = quotes_by_symbol.get(symbol)
                if quote is not None:
                    quotes_by_symbol[symbol] = enrich_with_yfinance_market_stats(quote, yfinance_stats.get(symbol))

        for symbol in symbols_needing_extended_fallback:
            quote = quotes_by_symbol.get(symbol)
            if quote is not None:
                quotes_by_symbol[symbol] = enrich_with_yahoo_extended_hours(quote, yahoo_quotes.get(symbol))

    return [quotes_by_symbol[symbol] for symbol in symbols if symbol in quotes_by_symbol]


