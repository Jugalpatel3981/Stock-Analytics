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
    StockPredictionResponse,
    StockSentimentTrendPoint,
    StockSearchResult,
)
from app.services import prediction_service, stock_service

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
    async def fake_search_stock_by_ticker(query: str) -> list[StockSearchResult]:
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
    monkeypatch.setattr(stock_service, "search_stock_by_ticker", fake_search_stock_by_ticker)

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
                    sentiment_label="Positive",
                    sentiment_score=0.87,
                )
            ],
            sentiment_trend=[
                StockSentimentTrendPoint(
                    date="2026-06-10",
                    positive=1,
                    neutral=0,
                    negative=0,
                    average_score=0.87,
                )
            ],
            sentiment_model="ProsusAI/finbert",
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
    assert payload["articles"][0]["sentiment_label"] == "Positive"
    assert payload["articles"][0]["sentiment_score"] == 0.87
    assert payload["sentiment_trend"][0]["positive"] == 1
    assert payload["sentiment_model"] == "ProsusAI/finbert"


def test_read_stock_prediction(monkeypatch) -> None:
    async def fake_get_stock_prediction(ticker: str) -> StockPredictionResponse:
        assert ticker == "tsla"
        return StockPredictionResponse(
            ticker=ticker.upper(),
            predicted_close=245.18,
            latest_close=240.52,
            confidence_score=87.4,
            historical_accuracy=84.2,
            training_rows=420,
            feature_summary=[
                "Historical close prices",
                "Trading volume",
                "5-day moving average",
            ],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(prediction_service, "get_stock_prediction", fake_get_stock_prediction)

    response = client.get("/api/v1/stocks/tsla/prediction")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "TSLA"
    assert payload["predicted_close"] == 245.18
    assert payload["confidence_score"] == 87.4
    assert payload["historical_accuracy"] == 84.2
    assert payload["model_name"] == "XGBoost Regressor"
