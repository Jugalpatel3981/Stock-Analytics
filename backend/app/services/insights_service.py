"""Analyst ratings, the next earnings date and key figures for one stock, from Finnhub."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.cache import TTLCache
from app.core.config import get_settings
from app.schemas.analytics import AnalystRatings, KeyMetrics, NextEarnings, StockInsights
from app.services import stock_service

EARNINGS_LOOKAHEAD_DAYS = 120

_insights_cache = TTLCache(ttl_seconds=30 * 60)


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _percent_to_fraction(value: Any) -> float | None:
    """Finnhub reports percentages as 27.6 for 27.6%."""
    number = _number(value)
    return round(number / 100, 4) if number is not None else None


def _latest_ratings(payload: Any) -> AnalystRatings | None:
    if not isinstance(payload, list):
        return None

    periods = [item for item in payload if isinstance(item, dict) and item.get("period")]
    if not periods:
        return None

    latest = max(periods, key=lambda item: str(item["period"]))
    ratings = AnalystRatings(
        period=str(latest["period"]),
        strong_buy=int(latest.get("strongBuy") or 0),
        buy=int(latest.get("buy") or 0),
        hold=int(latest.get("hold") or 0),
        sell=int(latest.get("sell") or 0),
        strong_sell=int(latest.get("strongSell") or 0),
    )
    total = ratings.strong_buy + ratings.buy + ratings.hold + ratings.sell + ratings.strong_sell
    return ratings if total > 0 else None


def _next_earnings(payload: Any, today: str) -> NextEarnings | None:
    items = payload.get("earningsCalendar") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None

    upcoming = sorted(
        (item for item in items if isinstance(item, dict) and str(item.get("date") or "") >= today),
        key=lambda item: str(item["date"]),
    )
    if not upcoming:
        return None

    return NextEarnings(
        date=str(upcoming[0]["date"]),
        eps_estimate=_number(upcoming[0].get("epsEstimate")),
        revenue_estimate=_number(upcoming[0].get("revenueEstimate")),
    )


def _key_metrics(payload: Any) -> KeyMetrics | None:
    metric = payload.get("metric") if isinstance(payload, dict) else None
    if not isinstance(metric, dict) or not metric:
        return None

    key_metrics = KeyMetrics(
        week_52_high=_number(metric.get("52WeekHigh")),
        week_52_high_date=metric.get("52WeekHighDate") or None,
        week_52_low=_number(metric.get("52WeekLow")),
        week_52_low_date=metric.get("52WeekLowDate") or None,
        dividend_yield=_percent_to_fraction(metric.get("dividendYieldIndicatedAnnual")),
        beta=_number(metric.get("beta")),
        eps_ttm=_number(metric.get("epsTTM")),
        net_margin=_percent_to_fraction(metric.get("netProfitMarginTTM")),
        revenue_growth_yoy=_percent_to_fraction(metric.get("revenueGrowthTTMYoy")),
    )
    has_values = any(value is not None for value in key_metrics.model_dump().values())
    return key_metrics if has_values else None


async def _load_insights(ticker: str) -> StockInsights:
    today = datetime.now(UTC).date()
    ratings, earnings, metric = await asyncio.gather(
        stock_service.finnhub_get("/stock/recommendation", {"symbol": ticker}),
        stock_service.finnhub_get(
            "/calendar/earnings",
            {
                "symbol": ticker,
                "from": today.isoformat(),
                "to": (today + timedelta(days=EARNINGS_LOOKAHEAD_DAYS)).isoformat(),
            },
        ),
        stock_service.finnhub_get("/stock/metric", {"symbol": ticker, "metric": "all"}),
        # One missing section should not hide the others.
        return_exceptions=True,
    )

    return StockInsights(
        ticker=ticker,
        analyst_ratings=_latest_ratings(ratings),
        next_earnings=_next_earnings(earnings, today.isoformat()),
        key_metrics=_key_metrics(metric),
    )


async def get_stock_insights(ticker: str) -> StockInsights:
    normalized_ticker = stock_service.normalize_ticker(ticker)
    if not get_settings().finnhub_api_key:
        return StockInsights(ticker=normalized_ticker, available=False)

    return await _insights_cache.get_or_set(
        normalized_ticker, lambda: _load_insights(normalized_ticker)
    )
