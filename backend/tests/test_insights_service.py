from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.services import insights_service, stock_service

TODAY = datetime.now(UTC).date()


def _use_finnhub(monkeypatch, responses: dict[str, object]) -> None:
    async def fake_finnhub_get(path: str, params: dict):
        response = responses[path]
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(get_settings(), "finnhub_api_key", "test-key")
    monkeypatch.setattr(stock_service, "finnhub_get", fake_finnhub_get)


async def test_insights_use_the_latest_ratings_next_earnings_and_key_metrics(monkeypatch) -> None:
    next_week = (TODAY + timedelta(days=7)).isoformat()
    next_quarter = (TODAY + timedelta(days=90)).isoformat()
    _use_finnhub(
        monkeypatch,
        {
            "/stock/recommendation": [
                {"period": "2026-09-01", "strongBuy": 1, "buy": 1, "hold": 1},
                {"period": "2026-11-01", "strongBuy": 11, "buy": 19, "hold": 15, "sell": 3},
            ],
            "/calendar/earnings": {
                "earningsCalendar": [
                    {"date": next_quarter, "epsEstimate": 3.1},
                    {"date": next_week, "epsEstimate": 2.96, "revenueEstimate": 159_000_000_000},
                ]
            },
            "/stock/metric": {
                "metric": {
                    "52WeekHigh": 355.91,
                    "52WeekHighDate": "2026-11-11",
                    "52WeekLow": 243.42,
                    "dividendYieldIndicatedAnnual": 0.5,
                    "netProfitMarginTTM": 27.6,
                    "beta": 1.09,
                }
            },
        },
    )

    insights = await insights_service.get_stock_insights("aapl")

    assert insights.ticker == "AAPL"
    assert insights.available is True
    assert insights.analyst_ratings.period == "2026-11-01"
    assert insights.analyst_ratings.buy == 19
    assert insights.analyst_ratings.strong_sell == 0
    assert insights.next_earnings.date == next_week
    assert insights.next_earnings.eps_estimate == 2.96
    assert insights.key_metrics.week_52_high == 355.91
    assert insights.key_metrics.dividend_yield == 0.005
    assert insights.key_metrics.net_margin == 0.276
    assert insights.key_metrics.revenue_growth_yoy is None


async def test_one_failing_section_does_not_hide_the_others(monkeypatch) -> None:
    _use_finnhub(
        monkeypatch,
        {
            "/stock/recommendation": ConnectionError("finnhub down"),
            "/calendar/earnings": {"earningsCalendar": []},
            "/stock/metric": {"metric": {"52WeekHigh": 781.6}},
        },
    )

    insights = await insights_service.get_stock_insights("SPY")

    assert insights.analyst_ratings is None
    assert insights.next_earnings is None
    assert insights.key_metrics.week_52_high == 781.6


async def test_empty_answers_become_missing_sections(monkeypatch) -> None:
    _use_finnhub(
        monkeypatch,
        {"/stock/recommendation": [], "/calendar/earnings": {}, "/stock/metric": {"metric": {}}},
    )

    insights = await insights_service.get_stock_insights("SPY")

    assert insights.analyst_ratings is None
    assert insights.next_earnings is None
    assert insights.key_metrics is None


async def test_insights_are_marked_unavailable_without_a_finnhub_key(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "finnhub_api_key", None)

    insights = await insights_service.get_stock_insights("AAPL")

    assert insights.available is False
    assert insights.analyst_ratings is None
