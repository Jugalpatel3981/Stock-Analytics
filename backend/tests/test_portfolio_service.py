from datetime import date, timedelta

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.auth import UserCreate
from app.schemas.portfolio import PortfolioHoldingCreate, PortfolioHoldingUpdate
from app.services import portfolio_service, stock_service

USER_ID = 1
OTHER_USER_ID = 2


@pytest.fixture(autouse=True)
def fake_market(monkeypatch):
    """AAPL is the only real ticker and always trades at 200."""

    async def fake_ensure_ticker_exists(ticker: str) -> str:
        normalized_ticker = stock_service.normalize_ticker(ticker)
        if normalized_ticker != "AAPL":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

        return normalized_ticker

    async def fake_get_current_price(_symbol: str) -> float:
        return 200.0

    monkeypatch.setattr(stock_service, "ensure_ticker_exists", fake_ensure_ticker_exists)
    monkeypatch.setattr(portfolio_service, "get_current_price", fake_get_current_price)


def _holding(symbol: str = "AAPL", **overrides) -> PortfolioHoldingCreate:
    values = {"symbol": symbol, "quantity": 2, "buy_price": 100, "buy_date": date(2025, 1, 2)}
    return PortfolioHoldingCreate(**{**values, **overrides})


def test_buy_date_in_the_future_is_rejected() -> None:
    tomorrow = date.today() + timedelta(days=1)

    with pytest.raises(ValidationError, match="Buy date cannot be in the future"):
        _holding(buy_date=tomorrow)
    with pytest.raises(ValidationError, match="Buy date cannot be in the future"):
        PortfolioHoldingUpdate(buy_date=tomorrow)


def test_buy_date_today_is_allowed() -> None:
    assert _holding(buy_date=date.today()).buy_date == date.today()


async def test_create_holding_rejects_unknown_symbol_and_saves_nothing(db_session) -> None:
    with pytest.raises(HTTPException) as caught:
        await portfolio_service.create_holding(db_session, USER_ID, _holding("ZZZZQ"))

    assert caught.value.status_code == 404
    assert await portfolio_service.list_raw_holdings(db_session, USER_ID) == []


async def test_create_holding_normalizes_the_symbol(db_session) -> None:
    holding = await portfolio_service.create_holding(db_session, USER_ID, _holding(" aapl "))

    assert holding.symbol == "AAPL"
    assert holding.gain_loss == 200.0


async def test_update_holding_changes_only_the_given_fields(db_session) -> None:
    holding = await portfolio_service.create_holding(db_session, USER_ID, _holding())

    updated = await portfolio_service.update_holding(
        db_session, USER_ID, holding.id, PortfolioHoldingUpdate(quantity=5)
    )

    assert updated.quantity == 5
    assert updated.buy_price == 100
    assert updated.buy_date == date(2025, 1, 2)
    assert updated.cost_basis == 500
    assert updated.gain_loss == 500


async def test_a_user_cannot_update_someone_elses_holding(db_session) -> None:
    holding = await portfolio_service.create_holding(db_session, USER_ID, _holding())

    with pytest.raises(HTTPException) as caught:
        await portfolio_service.update_holding(
            db_session, OTHER_USER_ID, holding.id, PortfolioHoldingUpdate(quantity=5)
        )

    assert caught.value.status_code == 404
    saved = await portfolio_service.list_raw_holdings(db_session, USER_ID)
    assert saved[0].quantity == 2


def test_update_rejects_zero_or_negative_numbers() -> None:
    with pytest.raises(ValidationError):
        PortfolioHoldingUpdate(quantity=0)
    with pytest.raises(ValidationError):
        PortfolioHoldingUpdate(buy_price=-1)


@pytest.mark.parametrize("password", ["12345678", "abcdefgh", "!!!!!!!!"])
def test_registration_rejects_passwords_without_a_letter_and_a_number(password: str) -> None:
    with pytest.raises(ValidationError, match="at least one letter and one number"):
        UserCreate(name="Test User", email="test@example.com", password=password)


def test_registration_accepts_a_password_with_a_letter_and_a_number() -> None:
    user = UserCreate(name="Test User", email="test@example.com", password="passw0rd")

    assert user.password == "passw0rd"
