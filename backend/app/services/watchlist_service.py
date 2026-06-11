from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.watchlist import Watchlist, WatchlistStock


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


async def list_watchlists(session: AsyncSession, user_id: int) -> list[Watchlist]:
    result = await session.execute(
        select(Watchlist)
        .where(Watchlist.user_id == user_id)
        .options(selectinload(Watchlist.stocks))
        .order_by(Watchlist.created_at.desc())
    )
    return list(result.scalars().all())


async def get_watchlist(session: AsyncSession, user_id: int, watchlist_id: int) -> Watchlist:
    result = await session.execute(
        select(Watchlist)
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        .options(selectinload(Watchlist.stocks))
    )
    watchlist = result.scalar_one_or_none()

    if watchlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )

    return watchlist


async def create_watchlist(session: AsyncSession, user_id: int, name: str) -> Watchlist:
    watchlist = Watchlist(user_id=user_id, name=name.strip())
    session.add(watchlist)
    await session.commit()
    await session.refresh(watchlist, attribute_names=["stocks"])

    return watchlist


async def add_stock_to_watchlist(
    session: AsyncSession,
    user_id: int,
    watchlist_id: int,
    ticker: str,
) -> Watchlist:
    watchlist = await get_watchlist(session, user_id, watchlist_id)
    normalized_ticker = normalize_ticker(ticker)

    if any(stock.ticker == normalized_ticker for stock in watchlist.stocks):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{normalized_ticker} is already in this watchlist",
        )

    session.add(WatchlistStock(watchlist_id=watchlist.id, ticker=normalized_ticker))
    await session.commit()

    return await get_watchlist(session, user_id, watchlist_id)


async def remove_stock_from_watchlist(
    session: AsyncSession,
    user_id: int,
    watchlist_id: int,
    ticker: str,
) -> Watchlist:
    watchlist = await get_watchlist(session, user_id, watchlist_id)
    normalized_ticker = normalize_ticker(ticker)
    stock_to_remove = next((stock for stock in watchlist.stocks if stock.ticker == normalized_ticker), None)

    if stock_to_remove is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{normalized_ticker} is not in this watchlist",
        )

    await session.delete(stock_to_remove)
    await session.commit()

    return await get_watchlist(session, user_id, watchlist_id)
