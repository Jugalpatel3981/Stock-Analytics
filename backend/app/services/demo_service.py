"""Shared demo account so visitors can explore the app without registering."""

import secrets
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.portfolio import PortfolioHolding
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistStock
from app.services.user_service import get_user_by_email

DEMO_EMAIL = "demo@stockintel.app"
DEMO_NAME = "Demo Investor"
DEMO_WATCHLIST_NAME = "Tech Leaders"
DEMO_WATCHLIST_TICKERS = ("NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META")
# Example positions (symbol, quantity, buy price, buy date) for showcasing portfolio tracking.
DEMO_HOLDINGS = (
    ("NVDA", 15, 118.50, date(2025, 1, 6)),
    ("AAPL", 20, 185.20, date(2024, 11, 4)),
    ("MSFT", 8, 410.00, date(2024, 12, 2)),
    ("TSLA", 10, 240.00, date(2025, 2, 3)),
)


async def _count(session: AsyncSession, model: type, user_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(model).where(model.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_or_create_demo_user(session: AsyncSession) -> User:
    """Return the demo user, refilling sample data a previous visitor may have removed."""
    user = await get_user_by_email(session, DEMO_EMAIL)
    if user is None:
        # Random password: the demo account is only reachable through the demo login.
        user = User(
            name=DEMO_NAME,
            email=DEMO_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(32)),
        )
        session.add(user)
        await session.flush()

    if await _count(session, Watchlist, user.id) == 0:
        watchlist = Watchlist(user_id=user.id, name=DEMO_WATCHLIST_NAME)
        session.add(watchlist)
        await session.flush()
        session.add_all(
            WatchlistStock(watchlist_id=watchlist.id, ticker=ticker)
            for ticker in DEMO_WATCHLIST_TICKERS
        )

    if await _count(session, PortfolioHolding, user.id) == 0:
        session.add_all(
            PortfolioHolding(
                user_id=user.id,
                symbol=symbol,
                quantity=quantity,
                buy_price=buy_price,
                buy_date=buy_date,
            )
            for symbol, quantity, buy_price, buy_date in DEMO_HOLDINGS
        )

    await session.commit()
    await session.refresh(user)
    return user
