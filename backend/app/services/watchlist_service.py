from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.watchlist import Watchlist, WatchlistStock
from app.services import stock_service


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


async def _ensure_name_is_free(
    session: AsyncSession, user_id: int, name: str, ignore_id: int | None = None
) -> None:
    query = select(Watchlist.id).where(
        Watchlist.user_id == user_id, func.lower(Watchlist.name) == name.lower()
    )
    if ignore_id is not None:
        query = query.where(Watchlist.id != ignore_id)

    if (await session.execute(query)).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'You already have a watchlist named "{name}"',
        )


def _clean_name(name: str) -> str:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Watchlist name cannot be empty",
        )

    return cleaned_name


async def create_watchlist(session: AsyncSession, user_id: int, name: str) -> Watchlist:
    cleaned_name = _clean_name(name)
    await _ensure_name_is_free(session, user_id, cleaned_name)
    watchlist = Watchlist(user_id=user_id, name=cleaned_name)
    session.add(watchlist)
    await session.commit()
    await session.refresh(watchlist, attribute_names=["stocks"])

    return watchlist


async def rename_watchlist(
    session: AsyncSession, user_id: int, watchlist_id: int, name: str
) -> Watchlist:
    watchlist = await get_watchlist(session, user_id, watchlist_id)
    cleaned_name = _clean_name(name)
    await _ensure_name_is_free(session, user_id, cleaned_name, ignore_id=watchlist.id)

    watchlist.name = cleaned_name
    await session.commit()
    session.expire_all()

    return await get_watchlist(session, user_id, watchlist_id)


async def delete_watchlist(session: AsyncSession, user_id: int, watchlist_id: int) -> None:
    watchlist = await get_watchlist(session, user_id, watchlist_id)
    await session.delete(watchlist)
    await session.commit()


async def add_stock_to_watchlist(
    session: AsyncSession,
    user_id: int,
    watchlist_id: int,
    ticker: str,
) -> Watchlist:
    watchlist = await get_watchlist(session, user_id, watchlist_id)
    normalized_ticker = stock_service.normalize_ticker(ticker)

    if any(stock.ticker == normalized_ticker for stock in watchlist.stocks):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{normalized_ticker} is already in this watchlist",
        )

    await stock_service.ensure_ticker_exists(normalized_ticker)

    session.add(WatchlistStock(watchlist_id=watchlist.id, ticker=normalized_ticker))
    await session.commit()
    session.expire_all()

    return await get_watchlist(session, user_id, watchlist_id)


async def remove_stock_from_watchlist(
    session: AsyncSession,
    user_id: int,
    watchlist_id: int,
    ticker: str,
) -> Watchlist:
    watchlist = await get_watchlist(session, user_id, watchlist_id)
    normalized_ticker = stock_service.normalize_ticker(ticker)
    stock_to_remove = next(
        (stock for stock in watchlist.stocks if stock.ticker == normalized_ticker), None
    )

    if stock_to_remove is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{normalized_ticker} is not in this watchlist",
        )

    await session.delete(stock_to_remove)
    await session.commit()
    session.expire_all()

    return await get_watchlist(session, user_id, watchlist_id)
