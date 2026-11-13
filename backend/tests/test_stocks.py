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


def _use_finnhub(monkeypatch, responses: dict[str, object]) -> list[tuple[str, dict]]:
    """Pretend a Finnhub key is configured and answer requests from `responses` by path."""
    from app.core.config import get_settings

    calls: list[tuple[str, dict]] = []

    async def fake_finnhub_get(path: str, params: dict):
        calls.append((path, params))
        response = responses[path]
        return response(params) if callable(response) else response

    monkeypatch.setattr(get_settings(), "finnhub_api_key", "test-key")
    monkeypatch.setattr(stock_service, "finnhub_get", fake_finnhub_get)
    return calls


async def test_search_uses_finnhub_and_skips_duplicates_and_unsupported_types(monkeypatch) -> None:
    _use_finnhub(
        monkeypatch,
        {
            "/search": {
                "count": 4,
                "result": [
                    {"symbol": "DIS", "description": "WALT DISNEY CO/THE", "type": "Common Stock"},
                    {"symbol": "DIS", "description": "WALT DISNEY CO/THE", "type": "Common Stock"},
                    {"symbol": "DISW", "description": "Disney warrant", "type": "Warrant"},
                    {"symbol": "SPY", "description": "SPDR S&P 500 ETF Trust", "type": "ETP"},
                ],
            },
            "/quote": {"c": 101.5},
        },
    )

    results = await stock_service.search_stocks("disney")

    assert [result.ticker for result in results] == ["DIS", "SPY"]
    assert results[0].company_name == "The Walt Disney Co"
    assert results[0].current_price == 101.5
    assert results[1].company_name == "SPDR S&P 500 ETF Trust"


async def test_search_retries_with_other_spellings(monkeypatch) -> None:
    def search(params: dict) -> dict:
        if params["q"] == "coca-cola":
            return {
                "result": [{"symbol": "KO", "description": "Coca-Cola Co", "type": "Common Stock"}]
            }
        return {"result": []}

    calls = _use_finnhub(monkeypatch, {"/search": search, "/quote": {"c": 70.0}})

    results = await stock_service.search_stocks("coca cola")

    assert [result.ticker for result in results] == ["KO"]
    searched = [params["q"] for path, params in calls if path == "/search"]
    assert searched == ["coca cola", "coca-cola"]


async def test_search_returns_no_results_instead_of_an_error(monkeypatch) -> None:
    _use_finnhub(monkeypatch, {"/search": {"count": 0, "result": []}})

    assert await stock_service.search_stocks("zzzzqq") == []


async def test_search_falls_back_to_company_alias_without_finnhub(monkeypatch) -> None:
    from app.core.config import get_settings

    def fake_build_stock_detail(ticker: str) -> StockDetail:
        assert ticker == "NVDA"
        return StockDetail(ticker="NVDA", company_name="NVIDIA Corporation", current_price=210.73)

    monkeypatch.setattr(get_settings(), "finnhub_api_key", None)
    monkeypatch.setattr(stock_service, "_build_stock_detail", fake_build_stock_detail)

    results = await stock_service.search_stocks("nvidia")

    assert len(results) == 1
    assert results[0].ticker == "NVDA"
    assert results[0].company_name == "NVIDIA Corporation"


async def test_news_comes_from_finnhub_newest_first_without_duplicates(monkeypatch) -> None:
    calls = _use_finnhub(
        monkeypatch,
        {
            "/company-news": [
                {"headline": "Older story", "source": "CNBC", "datetime": 1794000000},
                {"headline": "Newest story", "source": "Yahoo", "datetime": 1794400000},
                {"headline": "newest story", "source": "Benzinga", "datetime": 1794300000},
                {"headline": "", "datetime": 1794500000},
            ]
        },
    )

    news = await stock_service.get_stock_news("aapl", 5)

    assert news.ticker == "AAPL"
    assert news.data_source == "Finnhub"
    assert [article.headline for article in news.articles] == ["Newest story", "Older story"]
    assert news.articles[0].source == "Yahoo"
    assert news.articles[0].publish_date.startswith("2026-")
    assert calls[0][1]["symbol"] == "AAPL"


async def test_news_repairs_text_with_broken_encoding(monkeypatch) -> None:
    broken = "Apple’s market cap".encode().decode("latin-1")
    assert broken != "Apple’s market cap"
    _use_finnhub(
        monkeypatch,
        {
            "/company-news": [
                {"headline": "Plain café headline", "summary": broken, "datetime": 2},
                {"headline": broken, "summary": "ok", "datetime": 1},
            ]
        },
    )

    news = await stock_service.get_stock_news("AAPL", 5)

    assert news.articles[0].headline == "Plain café headline"
    assert news.articles[0].summary == "Apple’s market cap"
    assert news.articles[1].headline == "Apple’s market cap"


async def test_news_respects_the_limit(monkeypatch) -> None:
    _use_finnhub(
        monkeypatch,
        {"/company-news": [{"headline": f"Story {n}", "datetime": n} for n in range(1, 30)]},
    )

    news = await stock_service.get_stock_news("AAPL", 3)

    assert [article.headline for article in news.articles] == ["Story 29", "Story 28", "Story 27"]


async def test_news_provider_failure_is_reported_not_hidden(monkeypatch) -> None:
    import pytest
    from fastapi import HTTPException

    def broken(_params: dict):
        raise ConnectionError("finnhub down")

    _use_finnhub(monkeypatch, {"/company-news": broken})

    with pytest.raises(HTTPException) as caught:
        await stock_service.get_stock_news("AAPL", 5)

    assert caught.value.status_code == 502


async def test_ensure_ticker_exists_accepts_a_symbol_finnhub_prices(monkeypatch) -> None:
    def must_not_call_yahoo(_ticker: str):
        raise AssertionError("Yahoo should not be needed")

    _use_finnhub(monkeypatch, {"/quote": {"c": 355.6}})
    monkeypatch.setattr(stock_service, "_build_stock_detail", must_not_call_yahoo)

    assert await stock_service.ensure_ticker_exists(" aapl ") == "AAPL"


async def test_ensure_ticker_exists_checks_yahoo_when_finnhub_has_no_price(monkeypatch) -> None:
    _use_finnhub(monkeypatch, {"/quote": {"c": 0}})
    monkeypatch.setattr(
        stock_service,
        "_build_stock_detail",
        lambda ticker: StockDetail(ticker=ticker, company_name="Bitcoin USD", current_price=7.0),
    )

    assert await stock_service.ensure_ticker_exists("btc-usd") == "BTC-USD"


async def test_ensure_ticker_exists_rejects_unknown_and_remembers_it(monkeypatch) -> None:
    import pytest
    from fastapi import HTTPException, status

    yahoo_calls = []

    def unknown(ticker: str):
        yahoo_calls.append(ticker)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    _use_finnhub(monkeypatch, {"/quote": {"c": 0}})
    monkeypatch.setattr(stock_service, "_build_stock_detail", unknown)

    for _attempt in range(2):
        with pytest.raises(HTTPException) as caught:
            await stock_service.ensure_ticker_exists("ZZZZQ")
        assert caught.value.status_code == 404

    assert len(yahoo_calls) == 1


async def test_ensure_ticker_exists_rejects_malformed_symbols_without_a_lookup(monkeypatch) -> None:
    import pytest
    from fastapi import HTTPException

    calls = _use_finnhub(monkeypatch, {"/quote": {"c": 1.0}})

    with pytest.raises(HTTPException) as caught:
        await stock_service.ensure_ticker_exists("NOT A TICKER!")

    assert caught.value.status_code == 404
    assert calls == []


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


def test_history_skips_rows_with_missing_prices(monkeypatch) -> None:
    import pandas as pd

    class FakeTicker:
        def __init__(self, _ticker: str) -> None:
            pass

        def history(self, **_kwargs) -> pd.DataFrame:
            return pd.DataFrame(
                {
                    "Open": [100.0, float("nan"), 102.0],
                    "High": [101.0, float("nan"), 103.0],
                    "Low": [99.0, float("nan"), 101.0],
                    "Close": [100.5, float("nan"), 102.5],
                    "Volume": [1000, float("nan"), 1200],
                },
                index=pd.to_datetime(["2026-11-10", "2026-11-11", "2026-11-12"]),
            )

    monkeypatch.setattr(stock_service.yf, "Ticker", FakeTicker)

    history = stock_service._build_stock_history("AAPL", "1mo")
    closes = stock_service._build_daily_closes("AAPL", "1y")

    assert [point.close for point in history.prices] == [100.5, 102.5]
    assert history.prices[0].volume == 1000
    assert closes == {"2026-11-10": 100.5, "2026-11-12": 102.5}
    # The response must be valid JSON, which rejects NaN.
    assert "NaN" not in history.model_dump_json()


def test_to_float_rejects_values_that_are_not_finite_numbers() -> None:
    assert stock_service._to_float("12.5") == 12.5
    assert stock_service._to_float(float("nan")) is None
    assert stock_service._to_float(float("inf")) is None
    assert stock_service._to_float("N/A") is None
