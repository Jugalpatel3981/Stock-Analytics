from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.portfolio import PortfolioHolding
from app.models.watchlist import WatchlistStock


async def get_tracked_symbols(session: AsyncSession) -> list[str]:
    settings = get_settings()
    symbols = set(settings.default_ml_symbols)

    watchlist_result = await session.execute(select(WatchlistStock.ticker).distinct())
    symbols.update(symbol.upper() for symbol in watchlist_result.scalars().all() if symbol)

    portfolio_result = await session.execute(select(PortfolioHolding.symbol).distinct())
    symbols.update(symbol.upper() for symbol in portfolio_result.scalars().all() if symbol)

    return sorted(symbols)
