from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.watchlist import WatchlistCreate, WatchlistRead, WatchlistStockCreate
from app.services import watchlist_service

router = APIRouter()


@router.get("", response_model=list[WatchlistRead])
async def list_watchlists(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[WatchlistRead]:
    return await watchlist_service.list_watchlists(session, current_user.id)


@router.post("", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    watchlist_create: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WatchlistRead:
    return await watchlist_service.create_watchlist(session, current_user.id, watchlist_create.name)


@router.get("/{watchlist_id}", response_model=WatchlistRead)
async def read_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WatchlistRead:
    return await watchlist_service.get_watchlist(session, current_user.id, watchlist_id)


@router.post("/{watchlist_id}/stocks", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED)
async def add_stock_to_watchlist(
    watchlist_id: int,
    stock_create: WatchlistStockCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WatchlistRead:
    return await watchlist_service.add_stock_to_watchlist(
        session,
        current_user.id,
        watchlist_id,
        stock_create.ticker,
    )


@router.delete("/{watchlist_id}/stocks/{ticker}", response_model=WatchlistRead)
async def remove_stock_from_watchlist(
    watchlist_id: int,
    ticker: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WatchlistRead:
    return await watchlist_service.remove_stock_from_watchlist(
        session,
        current_user.id,
        watchlist_id,
        ticker,
    )
