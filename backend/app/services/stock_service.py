import asyncio
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import yfinance as yf
from fastapi import HTTPException, status

from app.core.cache import TTLCache
from app.core.config import get_settings
from app.schemas.stock import (
    HistoricalPricePoint,
    StockDetail,
    StockHistoryResponse,
    StockNewsItem,
    StockNewsResponse,
    StockSearchResult,
)

logger = logging.getLogger(__name__)

# Upper bound for one yfinance call, so a slow provider cannot stall whole pages.
YAHOO_TIMEOUT_SECONDS = 12

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
FINNHUB_TIMEOUT_SECONDS = 10
# Finnhub security types that the app can show a detail page for.
FINNHUB_SEARCH_TYPES = {"Common Stock", "ETP", "ADR", "REIT"}
MAX_SEARCH_RESULTS = 6
NEWS_LOOKBACK_DAYS = 7
TICKER_PATTERN = re.compile(r"[A-Z0-9^][A-Z0-9.\-=^]{0,11}")

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
_unknown_ticker_cache = TTLCache(ttl_seconds=10 * 60)
INTRADAY_HISTORY_TTL_SECONDS = 60

HISTORY_RANGES = {
    "1d": {"period": "1d", "interval": "5m"},
    "1wk": {"period": "5d", "interval": "30m"},
    "1mo": {"period": "1mo", "interval": "1d"},
    "1y": {"period": "1y", "interval": "1d"},
}


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


async def _finnhub_get(path: str, params: dict[str, Any]) -> Any:
    """Call the Finnhub REST API. Raises if no API key is configured or the call fails."""
    api_key = get_settings().finnhub_api_key
    if not api_key:
        raise RuntimeError("Finnhub API key is not configured.")

    async with httpx.AsyncClient(timeout=FINNHUB_TIMEOUT_SECONDS) as client:
        response = await client.get(
            f"{FINNHUB_BASE_URL}{path}", params={**params, "token": api_key}
        )
        response.raise_for_status()
        return response.json()


async def _finnhub_price(symbol: str) -> float | None:
    try:
        payload = await _finnhub_get("/quote", {"symbol": symbol})
    except Exception:
        return None

    price = _to_float(payload.get("c")) if isinstance(payload, dict) else None
    return price if price and price > 0 else None


def _not_found(normalized_ticker: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Stock ticker '{normalized_ticker}' was not found",
    )


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
        raise _not_found(normalized_ticker)

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
        "regular_price": _to_float(info.get("regularMarketPrice") or info.get("currentPrice")),
        "pre_market_price": _to_float(info.get("preMarketPrice")),
        "post_market_price": _to_float(info.get("postMarketPrice")),
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


async def _from_yahoo[T](func: Callable[..., T], *args: Any) -> T:
    """Run a blocking yfinance call, turning network or parsing failures into a clean 502."""
    try:
        return await asyncio.wait_for(asyncio.to_thread(func, *args), YAHOO_TIMEOUT_SECONDS)
    except HTTPException:
        raise
    except TimeoutError as exc:
        logger.warning("Yahoo Finance request timed out in %s", func.__name__)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The market data provider is responding slowly. Please try again shortly.",
        ) from exc
    except Exception as exc:
        logger.warning("Yahoo Finance request failed in %s: %s", func.__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The market data provider is unavailable right now. Please try again shortly.",
        ) from exc


async def get_stock_detail(ticker: str) -> StockDetail:
    normalized_ticker = normalize_ticker(ticker)
    if _unknown_ticker_cache.get(normalized_ticker)[0]:
        raise _not_found(normalized_ticker)

    try:
        return await _detail_cache.get_or_set(
            normalized_ticker, lambda: _from_yahoo(_build_stock_detail, ticker)
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            # Yahoo takes several seconds to reject an unknown ticker, so remember the answer.
            _unknown_ticker_cache.set(normalized_ticker, True)
        raise


async def ensure_ticker_exists(ticker: str) -> str:
    """Return the normalized ticker, or raise 404 if no provider knows it.

    Finnhub answers in a fraction of a second for US stocks and ETFs. Anything it does not
    price (crypto, indices, foreign listings) is checked against Yahoo Finance instead.
    """
    normalized_ticker = normalize_ticker(ticker)
    if not TICKER_PATTERN.fullmatch(normalized_ticker):
        raise _not_found(normalized_ticker)

    if _detail_cache.get(normalized_ticker)[0] or await _finnhub_price(normalized_ticker):
        return normalized_ticker

    await get_stock_detail(normalized_ticker)
    return normalized_ticker


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


def _repair_text(text: str) -> str:
    """Undo mojibake such as "Appleâ\x80\x99s", where UTF-8 bytes were read as Latin-1."""
    if "â" not in text and "Ã" not in text:
        return text

    for encoding in ("latin-1", "cp1252"):
        try:
            return text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

    return text


def _news_items_from_finnhub(payload: Any, limit: int) -> list[StockNewsItem]:
    if not isinstance(payload, list):
        return []

    articles: list[StockNewsItem] = []
    seen_headlines: set[str] = set()
    newest_first = sorted(
        (item for item in payload if isinstance(item, dict)),
        key=lambda item: _to_float(item.get("datetime")) or 0,
        reverse=True,
    )

    for item in newest_first:
        headline = _repair_text(str(item.get("headline") or "")).strip()
        # Finnhub often lists the same story from several feeds.
        if not headline or headline.lower() in seen_headlines:
            continue

        seen_headlines.add(headline.lower())
        summary = _repair_text(str(item.get("summary") or "")).strip()
        articles.append(
            StockNewsItem(
                headline=headline,
                source=item.get("source") or None,
                publish_date=_to_publish_date(item.get("datetime")),
                summary=summary[:1000] or None,
                url=item.get("url") or None,
            )
        )
        if len(articles) >= limit:
            break

    return articles


async def get_stock_news(ticker: str, limit: int) -> StockNewsResponse:
    normalized_ticker = normalize_ticker(ticker)
    return await _news_cache.get_or_set(
        (normalized_ticker, limit), lambda: _load_stock_news(normalized_ticker, limit)
    )


async def _load_stock_news(normalized_ticker: str, limit: int) -> StockNewsResponse:
    if get_settings().finnhub_api_key:
        today = datetime.now(UTC).date()
        try:
            payload = await _finnhub_get(
                "/company-news",
                {
                    "symbol": normalized_ticker,
                    "from": (today - timedelta(days=NEWS_LOOKBACK_DAYS)).isoformat(),
                    "to": today.isoformat(),
                },
            )
        except Exception as exc:
            logger.warning("Finnhub news request failed for %s: %s", normalized_ticker, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The news provider is unavailable right now. Please try again shortly.",
            ) from exc

        return StockNewsResponse(
            ticker=normalized_ticker,
            articles=_news_items_from_finnhub(payload, limit),
            data_source="Finnhub",
        )

    articles = await _from_yahoo(_build_stock_news_items, normalized_ticker, limit)
    return StockNewsResponse(ticker=normalized_ticker, articles=articles)


def _display_company_name(description: str) -> str:
    """Finnhub returns names in capitals, such as "WALT DISNEY CO/THE"."""
    name = description.strip()
    has_trailing_article = name.upper().endswith("/THE")
    if has_trailing_article:
        name = name[:-4]
    if name.isupper():
        name = name.title()

    return f"The {name}" if has_trailing_article else name


def _search_results_from_finnhub(payload: Any) -> list[StockSearchResult]:
    items = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    results: list[StockSearchResult] = []
    seen_symbols: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        symbol = str(item.get("symbol") or "").strip().upper()
        if (
            not symbol
            or symbol in seen_symbols
            or str(item.get("type") or "") not in FINNHUB_SEARCH_TYPES
        ):
            continue

        seen_symbols.add(symbol)
        results.append(
            StockSearchResult(
                ticker=symbol,
                company_name=_display_company_name(str(item.get("description") or "")) or None,
            )
        )
        if len(results) >= MAX_SEARCH_RESULTS:
            break

    return results


def _search_query_variants(query: str) -> list[str]:
    """Spellings to try in turn. Finnhub matches "coca-cola" and "jpmorgan" but not
    "coca cola" or "jp morgan"."""
    words = query.split()
    variants = [query]
    if len(words) > 1:
        variants += ["-".join(words), "".join(words), words[0]]

    return list(dict.fromkeys(variants))


async def _search_finnhub(query: str) -> list[StockSearchResult]:
    results: list[StockSearchResult] = []
    for variant in _search_query_variants(query):
        payload = await _finnhub_get("/search", {"q": variant, "exchange": "US"})
        results = _search_results_from_finnhub(payload)
        if results:
            break

    prices = await asyncio.gather(*(_finnhub_price(result.ticker) for result in results))

    return [
        result.model_copy(update={"current_price": price, "currency": "USD"})
        for result, price in zip(results, prices, strict=True)
    ]


def _search_exact_ticker(query: str) -> list[StockSearchResult]:
    """Fallback without Finnhub: treat the query as a ticker or a well-known company name."""
    alias_symbol = COMPANY_SYMBOL_ALIASES.get(query.lower())
    detail = _build_stock_detail(alias_symbol or query)
    return [
        StockSearchResult(
            ticker=detail.ticker,
            company_name=detail.company_name,
            exchange=detail.exchange,
            currency=detail.currency,
            current_price=detail.current_price,
        )
    ]


async def _load_search_results(query: str) -> list[StockSearchResult]:
    if get_settings().finnhub_api_key:
        try:
            return await _search_finnhub(query)
        except Exception as exc:
            logger.warning("Finnhub search failed for %r: %s", query, exc)

    try:
        return await _from_yahoo(_search_exact_ticker, query)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return []
        raise


async def search_stocks(query: str) -> list[StockSearchResult]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    return await _search_cache.get_or_set(
        normalized_query.lower(), lambda: _load_search_results(normalized_query)
    )
