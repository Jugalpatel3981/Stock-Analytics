from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioGrowthPoint,
    PortfolioGrowthResponse,
    PortfolioHoldingCreate,
    PortfolioHoldingRead,
    PortfolioSummary,
)
from app.services import portfolio_service

client = TestClient(app)


def override_current_user() -> User:
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        password_hash="hashed",
        created_at=datetime.now(UTC),
    )


def build_holding() -> PortfolioHoldingRead:
    return PortfolioHoldingRead(
        id=1,
        symbol="NVDA",
        quantity=2,
        buy_price=100,
        buy_date=date(2025, 1, 1),
        current_price=150,
        current_value=300,
        cost_basis=200,
        gain_loss=100,
        percentage_return=50,
        created_at=datetime.now(UTC),
    )


def test_portfolio_requires_authentication() -> None:
    response = client.get("/api/v1/portfolio/holdings")

    assert response.status_code == 401


def test_list_portfolio_holdings(monkeypatch) -> None:
    async def fake_get_portfolio_summary(session, user_id: int) -> PortfolioSummary:
        assert user_id == 1
        return PortfolioSummary(
            total_value=300,
            total_cost=200,
            total_gain_loss=100,
            total_percentage_return=50,
            holdings=[build_holding()],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(portfolio_service, "get_portfolio_summary", fake_get_portfolio_summary)

    response = client.get("/api/v1/portfolio/holdings")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_value"] == 300
    assert payload["holdings"][0]["symbol"] == "NVDA"


def test_create_portfolio_holding(monkeypatch) -> None:
    async def fake_create_holding(
        session,
        user_id: int,
        holding_create: PortfolioHoldingCreate,
    ) -> PortfolioHoldingRead:
        assert user_id == 1
        assert holding_create.symbol == "NVDA"
        return build_holding()

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(portfolio_service, "create_holding", fake_create_holding)

    response = client.post(
        "/api/v1/portfolio/holdings",
        json={
            "symbol": "NVDA",
            "quantity": 2,
            "buy_price": 100,
            "buy_date": "2025-01-01",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["gain_loss"] == 100


def test_portfolio_growth(monkeypatch) -> None:
    async def fake_get_portfolio_growth(session, user_id: int) -> PortfolioGrowthResponse:
        assert user_id == 1
        return PortfolioGrowthResponse(
            points=[
                PortfolioGrowthPoint(date="2025-01-01", value=200),
                PortfolioGrowthPoint(date="2025-01-02", value=210),
            ]
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(portfolio_service, "get_portfolio_growth", fake_get_portfolio_growth)

    response = client.get("/api/v1/portfolio/growth")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["points"][1]["value"] == 210
