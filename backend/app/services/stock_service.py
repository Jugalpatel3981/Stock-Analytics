import asyncio
from datetime import UTC, datetime
from typing import Any

import yfinance as yf
from fastapi import HTTPException, status

from app.schemas.stock import (
    HistoricalPricePoint,
    StockDetail,
    StockHistoryResponse,
    StockNewsItem,
    StockNewsResponse,
    StockSentimentTrendPoint,
    StockSearchResult,
)
from app.core.config import get_settings
from app.services import sentiment_service

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
                publish_date=_to_publish_date(content.get("pubDate") or article.get("providerPublishTime")),
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
            average_score=round(values["score_total"] / values["count"], 4) if values["count"] else 0.0,
        )
        for day, values in sorted(grouped.items())
    ]


async def get_stock_detail(ticker: str) -> StockDetail:
    return await asyncio.to_thread(_build_stock_detail, ticker)


async def get_stock_history(ticker: str, range_key: str) -> StockHistoryResponse:
    return await asyncio.to_thread(_build_stock_history, ticker, range_key)


async def get_stock_news(ticker: str, limit: int) -> StockNewsResponse:
    normalized_ticker = normalize_ticker(ticker)
    articles = await asyncio.to_thread(_build_stock_news_items, normalized_ticker, limit)

    enriched_articles: list[StockNewsItem] = []
    for article in articles:
        sentiment = await sentiment_service.analyze_sentiment(_build_sentiment_input(article))
        enriched_articles.append(
            article.model_copy(
                update={
                    "sentiment_label": sentiment.label,
                    "sentiment_score": sentiment.score,
                }
            )
        )

    return StockNewsResponse(
        ticker=normalized_ticker,
        articles=enriched_articles,
        sentiment_trend=_build_sentiment_trend(enriched_articles),
        sentiment_model=get_settings().huggingface_sentiment_model,
    )


async def search_stock_by_ticker(query: str) -> list[StockSearchResult]:
    detail = await get_stock_detail(query)
    return [
        StockSearchResult(
            ticker=detail.ticker,
            company_name=detail.company_name,
            exchange=detail.exchange,
            currency=detail.currency,
            current_price=detail.current_price,
        )
    ]
