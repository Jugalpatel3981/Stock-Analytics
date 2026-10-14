import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.portfolio import PortfolioHolding
from app.models.watchlist import Watchlist, WatchlistStock
from app.services import demo_service


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(engine, expire_on_commit=False)() as db_session:
        yield db_session

    await engine.dispose()


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_demo_user_is_created_once_with_sample_data(session) -> None:
    first = await demo_service.get_or_create_demo_user(session)
    second = await demo_service.get_or_create_demo_user(session)

    assert first.id == second.id
    assert first.email == demo_service.DEMO_EMAIL
    assert await _count(session, Watchlist) == 1
    assert await _count(session, WatchlistStock) == len(demo_service.DEMO_WATCHLIST_TICKERS)
    assert await _count(session, PortfolioHolding) == len(demo_service.DEMO_HOLDINGS)


async def test_demo_data_is_refilled_after_a_visitor_removes_it(session) -> None:
    user = await demo_service.get_or_create_demo_user(session)
    await session.execute(delete(PortfolioHolding).where(PortfolioHolding.user_id == user.id))
    await session.commit()

    await demo_service.get_or_create_demo_user(session)

    assert await _count(session, PortfolioHolding) == len(demo_service.DEMO_HOLDINGS)
    assert await _count(session, Watchlist) == 1
