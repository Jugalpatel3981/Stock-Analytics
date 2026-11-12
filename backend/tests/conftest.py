import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.cache import clear_all_caches
from app.core.rate_limit import reset_all_rate_limits
from app.models.base import Base


@pytest.fixture(autouse=True)
def isolate_shared_state():
    clear_all_caches()
    reset_all_rate_limits()
    yield
    clear_all_caches()
    reset_all_rate_limits()


@pytest.fixture
async def db_session():
    """An empty in-memory database with the full schema."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session

    await engine.dispose()
