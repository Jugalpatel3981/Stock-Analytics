from datetime import date, timedelta

import pytest
from fastapi import HTTPException, status

from app.models.portfolio import PortfolioHolding
from app.schemas.stock import StockDetail
from app.services import analytics_service, stock_service

USER_ID = 1
START = date(2026, 1, 1)
DAYS = 60


def _closes(start_price: float, daily_change: float, days: int = DAYS) -> dict[str, float]:
    """A price that changes by a fixed amount every day."""
    return {
        (START + timedelta(days=day)).isoformat(): start_price + daily_change * day
        for day in range(days)
    }


def _wavy(start_price: float, swing: float) -> dict[str, float]:
    """A price that alternates up and down, so it has real volatility."""
    return {
        (START + timedelta(days=day)).isoformat(): start_price + (swing if day % 2 else 0) + day
        for day in range(DAYS)
    }


PRICES = {
    "AAA": _wavy(100, 4),
    "BBB": _wavy(50, 1),
    "SPY": _wavy(400, 6),
}
SECTORS = {"AAA": "Technology", "BBB": "Energy"}


@pytest.fixture(autouse=True)
def fake_market(monkeypatch):
    async def fake_get_daily_closes(ticker: str, period: str = "1y") -> dict[str, float]:
        if ticker not in PRICES:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        return PRICES[ticker]

    async def fake_get_stock_detail(ticker: str) -> StockDetail:
        return StockDetail(
            ticker=ticker,
            company_name=f"{ticker} Inc",
            sector=SECTORS.get(ticker),
            market_cap=1_000,
            pe_ratio=20.0,
        )

    monkeypatch.setattr(stock_service, "get_daily_closes", fake_get_daily_closes)
    monkeypatch.setattr(stock_service, "get_stock_detail", fake_get_stock_detail)


async def _add(session, symbol: str, quantity: float, buy_price: float, buy_date: date) -> None:
    session.add(
        PortfolioHolding(
            user_id=USER_ID,
            symbol=symbol,
            quantity=quantity,
            buy_price=buy_price,
            buy_date=buy_date,
        )
    )
    await session.commit()


async def test_empty_portfolio_returns_an_empty_analysis(db_session) -> None:
    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    assert analytics.holdings == []
    assert analytics.performance == []
    assert analytics.since_purchase is None
    assert analytics.benchmark_symbol == "SPY"


async def test_since_purchase_compares_the_same_money_in_the_benchmark(db_session) -> None:
    # 10 shares bought at 100 on day 0. AAA ends at 163 (100 + 4 + 59).
    # SPY goes from 400 to 465 (400 + 6 + 59), so 1,000 in SPY becomes 1,162.50.
    await _add(db_session, "AAA", 10, 100.0, START)

    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    comparison = analytics.since_purchase
    assert comparison.invested == 1000.0
    assert comparison.portfolio_value == 1630.0
    assert comparison.portfolio_return == pytest.approx(0.63)
    assert comparison.benchmark_value == pytest.approx(1162.5)
    assert comparison.benchmark_return == pytest.approx(0.1625)

    holding = analytics.holdings[0]
    assert holding.symbol == "AAA"
    assert holding.gain == 630.0
    assert holding.excess_return == pytest.approx(0.63 - 0.1625)
    assert holding.weight == 1.0


async def test_lots_of_the_same_stock_are_combined(db_session) -> None:
    await _add(db_session, "AAA", 10, 100.0, START)
    await _add(db_session, "AAA", 5, 120.0, START + timedelta(days=20))

    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    assert len(analytics.holdings) == 1
    assert analytics.holdings[0].quantity == 15
    assert analytics.holdings[0].cost_basis == 1600.0
    assert analytics.holdings[0].value == 15 * 163


async def test_performance_is_rebased_to_100_and_risk_is_reported(db_session) -> None:
    await _add(db_session, "AAA", 10, 100.0, START)
    await _add(db_session, "BBB", 20, 50.0, START)

    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    assert len(analytics.performance) == DAYS
    assert analytics.performance[0].portfolio == 100.0
    assert analytics.performance[0].benchmark == 100.0
    assert analytics.window_start == START.isoformat()
    # Day 0 value 10*100 + 20*50 = 2,000; last day 10*163 + 20*110 = 3,830.
    assert analytics.portfolio.total_return == pytest.approx(0.915)
    assert analytics.portfolio.volatility > 0
    assert analytics.portfolio.max_drawdown < 0
    assert analytics.benchmark.total_return == pytest.approx(0.1625)
    assert analytics.beta is not None


async def test_allocation_by_holding_and_sector_adds_up_to_one(db_session) -> None:
    await _add(db_session, "AAA", 10, 100.0, START)
    await _add(db_session, "BBB", 20, 50.0, START)

    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    by_holding = {slice_.label: slice_ for slice_ in analytics.allocation_by_holding}
    assert by_holding["AAA"].value == 1630.0
    assert by_holding["BBB"].value == 2200.0
    assert sum(slice_.weight for slice_ in analytics.allocation_by_holding) == pytest.approx(1.0)
    assert [slice_.label for slice_ in analytics.allocation_by_sector] == ["Energy", "Technology"]


async def test_a_balanced_portfolio_has_no_concentration_warning(db_session) -> None:
    # Three positions of about a third each, in two sectors.
    await _add(db_session, "AAA", 10, 100.0, START)
    await _add(db_session, "BBB", 15, 50.0, START)
    await _add(db_session, "SPY", 4, 400.0, START)

    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    assert max(slice_.weight for slice_ in analytics.allocation_by_holding) < 0.4
    assert analytics.warnings == []


async def test_concentration_is_flagged(db_session) -> None:
    await _add(db_session, "AAA", 100, 100.0, START)
    await _add(db_session, "BBB", 1, 50.0, START)

    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    assert any("AAA makes up 99%" in warning for warning in analytics.warnings)
    assert any("Technology sector" in warning for warning in analytics.warnings)


async def test_symbols_without_price_history_are_excluded_and_reported(db_session) -> None:
    await _add(db_session, "AAA", 10, 100.0, START)
    await _add(db_session, "GONE", 10, 5.0, START)

    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    assert analytics.excluded_symbols == ["GONE"]
    assert [holding.symbol for holding in analytics.holdings] == ["AAA"]
    assert any("GONE" in warning for warning in analytics.warnings)


async def test_purchase_before_the_benchmark_history_is_reported(db_session) -> None:
    await _add(db_session, "AAA", 10, 100.0, START - timedelta(days=400))

    analytics = await analytics_service.get_portfolio_analytics(db_session, USER_ID)

    assert analytics.since_purchase.benchmark_value is None
    assert analytics.holdings[0].benchmark_return is None
    assert analytics.holdings[0].return_since_purchase == pytest.approx(0.63)
    assert any("before the available S&P 500 history" in warning for warning in analytics.warnings)


def test_compare_needs_two_to_five_different_symbols() -> None:
    assert analytics_service.normalize_compare_symbols(" aaa, BBB ,aaa") == ["AAA", "BBB"]

    for symbols in ("AAA", "AAA,aaa", "A,B,C,D,E,F"):
        with pytest.raises(HTTPException) as caught:
            analytics_service.normalize_compare_symbols(symbols)
        assert caught.value.status_code == 422


async def test_compare_rebases_prices_and_reports_stats_and_correlation() -> None:
    comparison = await analytics_service.compare_stocks(["AAA", "BBB"], "1y")

    assert comparison.symbols == ["AAA", "BBB"]
    assert comparison.points[0] == {"date": START.isoformat(), "AAA": 100.0, "BBB": 100.0}
    assert comparison.points[-1]["AAA"] == 163.0
    assert comparison.points[-1]["BBB"] == 220.0

    stats = {item.symbol: item for item in comparison.stats}
    assert stats["AAA"].total_return == pytest.approx(0.63)
    assert stats["AAA"].current_price == 163.0
    assert stats["AAA"].company_name == "AAA Inc"
    assert stats["BBB"].total_return == pytest.approx(1.2)

    assert comparison.correlation.symbols == ["AAA", "BBB"]
    assert comparison.correlation.values[0][0] == 1.0
    assert comparison.correlation.values[0][1] == comparison.correlation.values[1][0]
    assert comparison.correlation.values[0][1] > 0.9


async def test_compare_reports_symbols_it_could_not_find() -> None:
    comparison = await analytics_service.compare_stocks(["AAA", "GONE", "BBB"], "1y")

    assert comparison.symbols == ["AAA", "BBB"]
    assert comparison.missing_symbols == ["GONE"]


async def test_compare_fails_clearly_when_fewer_than_two_symbols_have_prices() -> None:
    with pytest.raises(HTTPException) as caught:
        await analytics_service.compare_stocks(["AAA", "GONE"], "1y")

    assert caught.value.status_code == 404
    assert "GONE" in caught.value.detail
