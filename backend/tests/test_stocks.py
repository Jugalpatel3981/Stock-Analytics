from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User
from app.schemas.stock import (
    HistoricalPricePoint,
    StockDetail,
    StockHistoryResponse,
    StockNewsItem,
    StockNewsResponse,
    StockSearchResult,
)
from app.services import stock_service

client = TestClient(app)


def override_current_user() -> User:
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        password_hash="hashed",
        created_at=datetime.now(UTC),
    )


def test_stock_detail_requires_authentication() -> None:
    response = client.get("/api/v1/stocks/NVDA")

    assert response.status_code == 401


def test_read_stock_detail(monkeypatch) -> None:
    async def fake_get_stock_detail(ticker: str) -> StockDetail:
        return StockDetail(
            ticker=ticker.upper(),
            company_name="NVIDIA Corporation",
            exchange="NMS",
            currency="USD",
            current_price=123.45,
            volume=1000000,
            market_cap=3000000000,
            pe_ratio=42.1,
            sector="Technology",
            industry="Semiconductors",
            website="https://www.nvidia.com",
            business_summary="GPU and AI computing company.",
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(stock_service, "get_stock_detail", fake_get_stock_detail)

    response = client.get("/api/v1/stocks/nvda")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert payload["company_name"] == "NVIDIA Corporation"
    assert payload["current_price"] == 123.45
    assert payload["volume"] == 1000000
    assert payload["market_cap"] == 3000000000
    assert payload["pe_ratio"] == 42.1


def test_search_stock_by_ticker(monkeypatch) -> None:
    async def fake_search_stocks(query: str) -> list[StockSearchResult]:
        return [
            StockSearchResult(
                ticker=query.upper(),
                company_name="Apple Inc.",
                exchange="NMS",
                currency="USD",
                current_price=198.25,
            )
        ]

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(stock_service, "search_stocks", fake_search_stocks)

    response = client.get("/api/v1/stocks/search?query=aapl")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["ticker"] == "AAPL"


def test_read_stock_history(monkeypatch) -> None:
    async def fake_get_stock_history(ticker: str, range_key: str) -> StockHistoryResponse:
        return StockHistoryResponse(
            ticker=ticker.upper(),
            range=range_key,
            interval="1d",
            prices=[
                HistoricalPricePoint(
                    timestamp="2026-06-10T13:30:00+00:00",
                    open=100.0,
                    high=105.0,
                    low=99.5,
                    close=104.2,
                    volume=123456,
                )
            ],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(stock_service, "get_stock_history", fake_get_stock_history)

    response = client.get("/api/v1/stocks/msft/history?range=1mo")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "MSFT"
    assert payload["range"] == "1mo"
    assert payload["prices"][0]["open"] == 100.0
    assert payload["prices"][0]["high"] == 105.0
    assert payload["prices"][0]["low"] == 99.5
    assert payload["prices"][0]["close"] == 104.2


def test_read_stock_news(monkeypatch) -> None:
    async def fake_get_stock_news(ticker: str, limit: int) -> StockNewsResponse:
        assert ticker == "nvda"
        assert limit == 5
        return StockNewsResponse(
            ticker=ticker.upper(),
            articles=[
                StockNewsItem(
                    headline="NVIDIA shares rise after AI demand update",
                    source="Yahoo Finance",
                    publish_date="2026-06-10T13:30:00+00:00",
                    summary="Chip demand remained strong across data center customers.",
                    url="https://finance.yahoo.com/news/nvidia",
                )
            ],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(stock_service, "get_stock_news", fake_get_stock_news)

    response = client.get("/api/v1/stocks/news?ticker=nvda&limit=5")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert payload["articles"][0]["headline"] == "NVIDIA shares rise after AI demand update"
    assert payload["articles"][0]["source"] == "Yahoo Finance"


def test_search_stocks_by_company_name(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "quotes": [
                    {
                        "symbol": "NVDA",
                        "quoteType": "EQUITY",
                        "longname": "NVIDIA Corporation",
                        "exchange": "NMS",
                        "currency": "USD",
                        "regularMarketPrice": 210.73,
                    },
                    {
                        "symbol": "NVDA",
                        "quoteType": "EQUITY",
                        "longname": "NVIDIA Corporation",
                    },
                    {
                        "symbol": "NVDA240621C00100000",
                        "quoteType": "OPTION",
                    },
                ]
            }

    def fake_get(url: str, params: dict[str, object], timeout: int) -> FakeResponse:
        assert params["q"] == "nvidia"
        assert params["quotesCount"] == 8
        return FakeResponse()

    monkeypatch.setattr("httpx.get", fake_get)

    results = stock_service._search_stocks("nvidia")

    assert len(results) == 1
    assert results[0].ticker == "NVDA"
    assert results[0].company_name == "NVIDIA Corporation"
    assert results[0].current_price == 210.73


def test_search_stocks_uses_company_alias_when_yahoo_search_is_empty(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"quotes": []}

    def fake_get(url: str, params: dict[str, object], timeout: int) -> FakeResponse:
        return FakeResponse()

    def fake_build_stock_detail(ticker: str) -> StockDetail:
        assert ticker == "NVDA"
        return StockDetail(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            exchange="NMS",
            currency="USD",
            current_price=210.73,
        )

    monkeypatch.setattr("httpx.get", fake_get)
    monkeypatch.setattr(stock_service, "_build_stock_detail", fake_build_stock_detail)

    results = stock_service._search_stocks("nvidia")

    assert len(results) == 1
    assert results[0].ticker == "NVDA"
    assert results[0].company_name == "NVIDIA Corporation"


async def test_yahoo_failures_become_bad_gateway(monkeypatch) -> None:
    import pytest
    from fastapi import HTTPException

    def unreachable(_ticker: str):
        raise ConnectionError("tunnel failed")

    monkeypatch.setattr(stock_service, "_build_stock_detail", unreachable)

    with pytest.raises(HTTPException) as caught:
        await stock_service.get_stock_detail("NVDA")

    assert caught.value.status_code == 502


async def test_portfolio_price_is_none_when_provider_is_down(monkeypatch) -> None:
    from app.services import portfolio_service

    def unreachable(_ticker: str):
        raise ConnectionError("tunnel failed")

    monkeypatch.setattr(stock_service, "_build_stock_detail", unreachable)

    assert await portfolio_service.get_current_price("NVDA") is None


async def test_slow_yahoo_calls_time_out(monkeypatch) -> None:
    import time

    import pytest
    from fastapi import HTTPException

    def slow(_ticker: str):
        time.sleep(1)

    monkeypatch.setattr(stock_service, "YAHOO_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(stock_service, "_build_stock_detail", slow)

    with pytest.raises(HTTPException) as caught:
        await stock_service.get_stock_detail("NVDA")

    assert caught.value.status_code == 504
