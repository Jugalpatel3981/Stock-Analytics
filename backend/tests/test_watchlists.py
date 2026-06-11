from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User
from app.schemas.watchlist import WatchlistRead, WatchlistStockRead
from app.services import watchlist_service

client = TestClient(app)


def override_current_user() -> User:
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        password_hash="hashed",
        created_at=datetime.now(UTC),
    )


def build_watchlist(ticker: str | None = None) -> WatchlistRead:
    stocks = []
    if ticker is not None:
        stocks.append(
            WatchlistStockRead(
                id=1,
                ticker=ticker,
                added_at=datetime.now(UTC),
            )
        )

    return WatchlistRead(
        id=1,
        name="Growth Stocks",
        created_at=datetime.now(UTC),
        stocks=stocks,
    )


def test_watchlists_require_authentication() -> None:
    response = client.get("/api/v1/watchlists")

    assert response.status_code == 401


def test_create_watchlist(monkeypatch) -> None:
    async def fake_create_watchlist(session, user_id: int, name: str) -> WatchlistRead:
        assert user_id == 1
        assert name == "Growth Stocks"
        return build_watchlist()

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(watchlist_service, "create_watchlist", fake_create_watchlist)

    response = client.post("/api/v1/watchlists", json={"name": "Growth Stocks"})

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["name"] == "Growth Stocks"


def test_add_stock_to_watchlist(monkeypatch) -> None:
    async def fake_add_stock_to_watchlist(session, user_id: int, watchlist_id: int, ticker: str) -> WatchlistRead:
        assert user_id == 1
        assert watchlist_id == 1
        assert ticker == "nvda"
        return build_watchlist("NVDA")

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(watchlist_service, "add_stock_to_watchlist", fake_add_stock_to_watchlist)

    response = client.post("/api/v1/watchlists/1/stocks", json={"ticker": "nvda"})

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["stocks"][0]["ticker"] == "NVDA"


def test_remove_stock_from_watchlist(monkeypatch) -> None:
    async def fake_remove_stock_from_watchlist(session, user_id: int, watchlist_id: int, ticker: str) -> WatchlistRead:
        assert user_id == 1
        assert watchlist_id == 1
        assert ticker == "NVDA"
        return build_watchlist()

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(watchlist_service, "remove_stock_from_watchlist", fake_remove_stock_from_watchlist)

    response = client.delete("/api/v1/watchlists/1/stocks/NVDA")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["stocks"] == []
