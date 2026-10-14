from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import HistoricalPrice
from app.services.stock_service import normalize_ticker


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _download_history(ticker: str, period: str = "5y") -> list[dict[str, Any]]:
    history = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
    if history.empty:
        return []

    rows: list[dict[str, Any]] = []
    for timestamp, row in history.iterrows():
        open_price = _to_float(row.get("Open"))
        high_price = _to_float(row.get("High"))
        low_price = _to_float(row.get("Low"))
        close_price = _to_float(row.get("Close"))
        adjusted_close = _to_float(row.get("Adj Close")) or close_price

        if None in (open_price, high_price, low_price, close_price, adjusted_close):
            continue

        price_date = (
            timestamp.date()
            if hasattr(timestamp, "date")
            else date.fromisoformat(str(timestamp)[:10])
        )
        rows.append(
            {
                "ticker": ticker,
                "price_date": price_date,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "adjusted_close": adjusted_close,
                "volume": _to_int(row.get("Volume")),
            }
        )

    return rows


async def update_historical_data(session: AsyncSession, ticker: str, period: str = "5y") -> int:
    normalized_ticker = normalize_ticker(ticker)
    downloaded_rows = await asyncio.to_thread(_download_history, normalized_ticker, period)
    if not downloaded_rows:
        return 0

    result = await session.execute(
        select(HistoricalPrice).where(HistoricalPrice.ticker == normalized_ticker)
    )
    existing_by_date = {row.price_date: row for row in result.scalars().all()}
    changed_rows = 0

    for row in downloaded_rows:
        existing = existing_by_date.get(row["price_date"])
        if existing is None:
            session.add(HistoricalPrice(**row))
            changed_rows += 1
            continue

        for key in ("open", "high", "low", "close", "adjusted_close", "volume"):
            next_value = row[key]
            if getattr(existing, key) != next_value:
                setattr(existing, key, next_value)
                changed_rows += 1

    await session.commit()
    return changed_rows


async def load_price_history(session: AsyncSession, ticker: str) -> list[HistoricalPrice]:
    normalized_ticker = normalize_ticker(ticker)
    result = await session.execute(
        select(HistoricalPrice)
        .where(HistoricalPrice.ticker == normalized_ticker)
        .order_by(HistoricalPrice.price_date.asc())
    )
    return list(result.scalars().all())
