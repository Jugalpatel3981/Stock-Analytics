import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import yfinance as yf
from fastapi import HTTPException, status

from app.core.cache import TTLCache
from app.schemas.stock import (
    HistoricalPricePoint,
    StockDetail,
    StockHistoryResponse,
    StockNewsItem,
    StockNewsResponse,
    StockSearchResult,
    StockSentimentTrendPoint,
)
from app.services import sentiment_service

logger = logging.getLogger(__name__)

YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"

COMPANY_SYMBOL_ALIASES = {
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "amd": "AMD",
    "apple": "AAPL",
    "berkshire hathaway": "BRK-B",
    "facebook": "META",
    "google": "GOOGL",
    "jpmorgan": "JPM",
    "jpmorgan chase": "JPM",
    "meta": "META",
    "meta platforms": "META",
    "microsoft": "MSFT",
    "netflix": "NFLX",
    "nvidia": "NVDA",
    "tesla": "TSLA",
}

# Yahoo Finance is slow and rate-limits aggressively, especially from cloud servers.
_detail_cache = TTLCache(ttl_seconds=60)
_market_stats_cache = TTLCache(ttl_seconds=30)
_history_cache = TTLCache(ttl_seconds=15 * 60)
_news_cache = TTLCache(ttl_seconds=10 * 60)
_search_cache = TTLCache(ttl_seconds=60 * 60)
INTRADAY_HISTORY_TTL_SECONDS = 60

HISTORY_RANGES = {
    "1d": {"period": "1d", "interval": "5m"},
    "1wk": {"period": "5d", "interval": "30m"},
    "1mo": {"period": "1mo", "interval": "1d"},
    "1y": {"period": "1y", "interval": "1d"},
}


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def _read_fast_info_value(fast_info: Any, key: str) -> Any:
    try:
        return fast_info.get(key)
    except AttributeError:
        return getattr(fast_info, key, None)
    except Exception:
        return None


def _to_float(value: Any) -> float | None:
    if value in (None, "", "N/A"):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value in (None, "", "N/A"):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_nested_value(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload

    for key in keys:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


def _to_publish_date(value: Any) -> str | None:
    if value in (None, "", "N/A"):
        return None

    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, UTC).isoformat()

    return str(value)


def _extract_news_url(content: dict[str, Any], article: dict[str, Any]) -> str | None:
    return (
        _read_nested_value(content, "canonicalUrl", "url")
        or _read_nested_value(content, "clickThroughUrl", "url")
        or article.get("link")
    )


def _build_stock_detail(ticker: str) -> StockDetail:
    normalized_ticker = normalize_ticker(ticker)
    stock = yf.Ticker(normalized_ticker)
    info = stock.info or {}
    fast_info = stock.fast_info

    company_name = info.get("longName") or info.get("shortName")
    current_price = (
        _to_float(_read_fast_info_value(fast_info, "lastPrice"))
        or _to_float(info.get("currentPrice"))
        or _to_float(info.get("regularMarketPrice"))
    )

    if company_name is None and current_price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock ticker '{normalized_ticker}' was not found",
        )

    return StockDetail(
        ticker=normalized_ticker,
        company_name=company_name,
        exchange=info.get("exchange"),
        currency=info.get("currency") or _read_fast_info_value(fast_info, "currency"),
        current_price=current_price,
        volume=_to_int(info.get("volume") or info.get("regularMarketVolume")),
        market_cap=_to_int(info.get("marketCap")),
        pe_ratio=_to_float(info.get("trailingPE") or info.get("forwardPE")),
        sector=info.get("sector"),
        industry=info.get("industry"),
        website=info.get("website"),
        business_summary=info.get("longBusinessSummary"),
    )


def _latest_history_row(stock: yf.Ticker) -> dict[str, Any]:
    history = stock.history(period="1d", interval="1d", auto_adjust=False)
    if history.empty:
        return {}

    latest = history.tail(1).iloc[0]
    return {
        "open": latest.get("Open"),
        "high": latest.get("High"),
        "low": latest.get("Low"),
        "volume": latest.get("Volume"),
    }


def _build_stock_market_stats(ticker: str) -> dict[str, float | int | None]:
    normalized_ticker = normalize_ticker(ticker)
    stock = yf.Ticker(normalized_ticker)
    info = stock.info or {}
    fast_info = stock.fast_info
    latest_history = _latest_history_row(stock)

    return {
        "volume": _to_int(
            info.get("volume")
            or info.get("regularMarketVolume")
            or _read_fast_info_value(fast_info, "lastVolume")
            or latest_history.get("volume")
        ),
        "open": _to_float(
            info.get("open")
            or info.get("regularMarketOpen")
            or _read_fast_info_value(fast_info, "open")
            or latest_history.get("open")
        ),
        "high": _to_float(
            info.get("dayHigh")
            or info.get("regularMarketDayHigh")
            or _read_fast_info_value(fast_info, "dayHigh")
            or latest_history.get("high")
        ),
        "low": _to_float(
            info.get("dayLow")
            or info.get("regularMarketDayLow")
            or _read_fast_info_value(fast_info, "dayLow")
            or latest_history.get("low")
        ),
        "previous_close": _to_float(
            info.get("previousClose")
            or info.get("regularMarketPreviousClose")
            or _read_fast_info_value(fast_info, "previousClose")
        ),
    }


def _build_stock_history(ticker: str, range_key: str) -> StockHistoryResponse:
    normalized_ticker = normalize_ticker(ticker)
    history_config = HISTORY_RANGES[range_key]
    stock = yf.Ticker(normalized_ticker)
    history = stock.history(
        period=history_config["period"],
        interval=history_config["interval"],
        auto_adjust=False,
    )

    if history.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical prices for '{normalized_ticker}' were not found",
        )

    prices: list[HistoricalPricePoint] = []
    for timestamp, row in history.iterrows():
        open_price = _to_float(row.get("Open"))
        high_price = _to_float(row.get("High"))
        low_price = _to_float(row.get("Low"))
        close_price = _to_float(row.get("Close"))

        if None in (open_price, high_price, low_price, close_price):
            continue

        prices.append(
            HistoricalPricePoint(
                timestamp=timestamp.isoformat(),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=_to_int(row.get("Volume")),
            )
        )

    if not prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical prices for '{normalized_ticker}' were not found",
        )

    return StockHistoryResponse(
        ticker=normalized_ticker,
        range=range_key,
        interval=history_config["interval"],
        prices=prices,
    )


def _build_stock_news_items(ticker: str, limit: int) -> list[StockNewsItem]:
    normalized_ticker = normalize_ticker(ticker)
    stock = yf.Ticker(normalized_ticker)
    raw_articles = stock.news or []
    articles: list[StockNewsItem] = []

    for article in raw_articles[:limit]:
        content = article.get("content") if isinstance(article.get("content"), dict) else {}
        headline = content.get("title") or article.get("title")

        if not headline:
            continue

        articles.append(
            StockNewsItem(
                headline=headline,
                source=(
                    _read_nested_value(content, "provider", "displayName")
                    or content.get("publisher")
                    or article.get("publisher")
                ),
                publish_date=_to_publish_date(
                    content.get("pubDate") or article.get("providerPublishTime")
                ),
                summary=content.get("summary") or article.get("summary"),
                url=_extract_news_url(content, article),
            )
        )

    return articles


def _build_sentiment_input(article: StockNewsItem) -> str:
    return f"{article.headline}. {article.summary or ''}".strip()


def _build_sentiment_trend(articles: list[StockNewsItem]) -> list[StockSentimentTrendPoint]:
    grouped: dict[str, dict[str, float]] = {}

    for article in articles:
        if not article.publish_date:
            continue

        day = article.publish_date[:10]
        if day not in grouped:
            grouped[day] = {
                "Positive": 0,
                "Neutral": 0,
                "Negative": 0,
                "score_total": 0.0,
                "count": 0,
            }

        grouped[day][article.sentiment_label] += 1
        grouped[day]["score_total"] += article.sentiment_score
        grouped[day]["count"] += 1

    return [
        StockSentimentTrendPoint(
            date=day,
            positive=int(values["Positive"]),
            neutral=int(values["Neutral"]),
            negative=int(values["Negative"]),
            average_score=round(values["score_total"] / values["count"], 4)
            if values["count"]
            else 0.0,
        )
        for day, values in sorted(grouped.items())
    ]


async def _from_yahoo[T](func: Callable[..., T], *args: Any) -> T:
    """Run a blocking yfinance call, turning network or parsing failures into a clean 502."""
    try:
        return await asyncio.to_thread(func, *args)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Yahoo Finance request failed in %s: %s", func.__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The market data provider is unavailable right now. Please try again shortly.",
        ) from exc


async def get_stock_detail(ticker: str) -> StockDetail:
    return await _detail_cache.get_or_set(
        normalize_ticker(ticker), lambda: _from_yahoo(_build_stock_detail, ticker)
    )


async def get_stock_market_stats(ticker: str) -> dict[str, float | int | None]:
    return await _market_stats_cache.get_or_set(
        normalize_ticker(ticker), lambda: _from_yahoo(_build_stock_market_stats, ticker)
    )


async def get_stock_history(ticker: str, range_key: str) -> StockHistoryResponse:
    return await _history_cache.get_or_set(
        (normalize_ticker(ticker), range_key),
        lambda: _from_yahoo(_build_stock_history, ticker, range_key),
        INTRADAY_HISTORY_TTL_SECONDS if range_key == "1d" else None,
    )


async def get_stock_news(ticker: str, limit: int) -> StockNewsResponse:
    normalized_ticker = normalize_ticker(ticker)
    return await _news_cache.get_or_set(
        (normalized_ticker, limit), lambda: _load_stock_news(normalized_ticker, limit)
    )


async def _load_stock_news(normalized_ticker: str, limit: int) -> StockNewsResponse:
    articles = await _from_yahoo(_build_stock_news_items, normalized_ticker, limit)

    sentiments = await sentiment_service.analyze_sentiments(
        [_build_sentiment_input(article) for article in articles]
    )
    enriched_articles = [
        article.model_copy(
            update={
                "sentiment_label": sentiment.label,
                "sentiment_score": sentiment.score,
            }
        )
        for article, sentiment in zip(articles, sentiments, strict=True)
    ]

    return StockNewsResponse(
        ticker=normalized_ticker,
        articles=enriched_articles,
        sentiment_trend=_build_sentiment_trend(enriched_articles),
        sentiment_model=sentiment_service.sentiment_model_name(),
    )


def _build_search_result_from_quote(quote: dict[str, Any]) -> StockSearchResult | None:
    symbol = str(quote.get("symbol") or "").strip().upper()
    quote_type = str(quote.get("quoteType") or "").upper()

    if not symbol or quote_type not in {"EQUITY", "ETF"}:
        return None

    return StockSearchResult(
        ticker=symbol,
        company_name=quote.get("longname") or quote.get("shortname") or quote.get("name"),
        exchange=quote.get("exchange") or quote.get("exchDisp"),
        currency=quote.get("currency"),
        current_price=_to_float(quote.get("regularMarketPrice")),
    )


def _search_stocks(query: str) -> list[StockSearchResult]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    try:
        response = httpx.get(
            YAHOO_SEARCH_URL,
            params={"q": normalized_query, "quotesCount": 8, "newsCount": 0},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        results = []
        seen_symbols: set[str] = set()

        for quote in payload.get("quotes", []):
            if not isinstance(quote, dict):
                continue

            result = _build_search_result_from_quote(quote)
            if result is None or result.ticker in seen_symbols:
                continue

            seen_symbols.add(result.ticker)
            results.append(result)

        if results:
            return results
    except Exception:
        pass

    alias_symbol = COMPANY_SYMBOL_ALIASES.get(normalized_query.lower())
    detail = _build_stock_detail(alias_symbol or normalized_query)
    return [
        StockSearchResult(
            ticker=detail.ticker,
            company_name=detail.company_name,
            exchange=detail.exchange,
            currency=detail.currency,
            current_price=detail.current_price,
        )
    ]


async def search_stocks(query: str) -> list[StockSearchResult]:
    return await _search_cache.get_or_set(
        query.strip().lower(), lambda: _from_yahoo(_search_stocks, query)
    )


async def search_stock_by_ticker(query: str) -> list[StockSearchResult]:
    return await search_stocks(query)
