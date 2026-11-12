"""Portfolio analytics and stock comparison, built on daily closing prices."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import metrics
from app.models.portfolio import PortfolioHolding
from app.schemas.analytics import (
    AllocationSlice,
    ComparisonStats,
    CorrelationMatrix,
    HoldingPerformance,
    PerformancePoint,
    PortfolioAnalytics,
    PurchaseComparison,
    RiskMetrics,
    StockComparison,
)
from app.services import portfolio_service, stock_service

BENCHMARK_SYMBOL = "SPY"
# Five years of prices cover most purchase dates; risk figures use the most recent year.
HISTORY_PERIOD = "5y"
ANALYSIS_WINDOW_DAYS = metrics.TRADING_DAYS_PER_YEAR + 1
UNKNOWN_SECTOR = "Other"
MIN_COMPARE_SYMBOLS = 2
MAX_COMPARE_SYMBOLS = 5
# Above these shares of the portfolio, a single position or sector is flagged.
HOLDING_CONCENTRATION_LIMIT = 0.4
SECTOR_CONCENTRATION_LIMIT = 0.6


async def _load_closes(symbols: list[str], period: str) -> tuple[dict[str, pd.Series], list[str]]:
    """Daily closes per symbol, plus the symbols no price history could be loaded for."""
    results = await asyncio.gather(
        *(stock_service.get_daily_closes(symbol, period) for symbol in symbols),
        return_exceptions=True,
    )

    closes: dict[str, pd.Series] = {}
    missing: list[str] = []
    for symbol, result in zip(symbols, results, strict=True):
        if isinstance(result, dict) and len(result) >= 2:
            closes[symbol] = pd.Series(result, dtype=float).sort_index()
        else:
            missing.append(symbol)

    return closes, missing


def _aligned_frame(closes: dict[str, pd.Series], symbols: list[str]) -> pd.DataFrame:
    """Closes for `symbols` on the dates they all traded."""
    return pd.DataFrame({symbol: closes[symbol] for symbol in symbols}).dropna().sort_index()


def _risk_metrics(values: pd.Series) -> RiskMetrics:
    returns = metrics.daily_returns(values)
    has_returns = len(returns) > 0

    return RiskMetrics(
        total_return=metrics.round_or_none(metrics.total_return(values)),
        volatility=metrics.round_or_none(metrics.annualized_volatility(returns)),
        sharpe_ratio=metrics.round_or_none(metrics.sharpe_ratio(returns), 2),
        max_drawdown=metrics.round_or_none(metrics.max_drawdown(values)),
        best_day=metrics.round_or_none(float(returns.max())) if has_returns else None,
        worst_day=metrics.round_or_none(float(returns.min())) if has_returns else None,
    )


def _price_on_or_after(closes: pd.Series, day: date) -> float | None:
    """The first close on or after `day`, or None if `day` is before the history starts."""
    day_key = day.isoformat()
    if closes.empty or day_key < closes.index[0]:
        return None

    later = closes[closes.index >= day_key]
    return float(later.iloc[0]) if not later.empty else float(closes.iloc[-1])


def _slices(values: dict[str, float]) -> list[AllocationSlice]:
    total = sum(values.values())
    if total <= 0:
        return []

    return [
        AllocationSlice(label=label, value=round(value, 2), weight=round(value / total, 4))
        for label, value in sorted(values.items(), key=lambda item: item[1], reverse=True)
    ]


async def _sectors(symbols: list[str]) -> dict[str, str]:
    details = await asyncio.gather(
        *(stock_service.get_stock_detail(symbol) for symbol in symbols), return_exceptions=True
    )
    return {
        symbol: (getattr(detail, "sector", None) or UNKNOWN_SECTOR)
        for symbol, detail in zip(symbols, details, strict=True)
    }


def _holding_rows(
    holdings: list[PortfolioHolding],
    closes: dict[str, pd.Series],
    benchmark: pd.Series | None,
) -> tuple[list[HoldingPerformance], PurchaseComparison | None, bool]:
    """Per-symbol results since purchase, the portfolio total, and whether every lot
    could be compared with the benchmark."""
    lots_by_symbol: dict[str, list[PortfolioHolding]] = defaultdict(list)
    for holding in holdings:
        if holding.symbol in closes:
            lots_by_symbol[holding.symbol].append(holding)

    rows: list[HoldingPerformance] = []
    total_cost = 0.0
    total_value = 0.0
    total_benchmark_value = 0.0
    every_lot_comparable = benchmark is not None

    for symbol, lots in lots_by_symbol.items():
        latest_price = float(closes[symbol].iloc[-1])
        quantity = sum(lot.quantity for lot in lots)
        cost = sum(lot.quantity * lot.buy_price for lot in lots)
        value = quantity * latest_price

        benchmark_value: float | None = 0.0
        for lot in lots:
            start_price = (
                _price_on_or_after(benchmark, lot.buy_date) if benchmark is not None else None
            )
            if start_price is None or benchmark_value is None:
                benchmark_value = None
                continue

            benchmark_value += (
                lot.quantity * lot.buy_price * float(benchmark.iloc[-1]) / start_price
            )

        holding_return = value / cost - 1 if cost > 0 else None
        benchmark_return = (
            benchmark_value / cost - 1 if benchmark_value is not None and cost > 0 else None
        )
        rows.append(
            HoldingPerformance(
                symbol=symbol,
                quantity=quantity,
                cost_basis=round(cost, 2),
                value=round(value, 2),
                gain=round(value - cost, 2),
                return_since_purchase=metrics.round_or_none(holding_return),
                benchmark_return=metrics.round_or_none(benchmark_return),
                excess_return=metrics.round_or_none(
                    holding_return - benchmark_return
                    if holding_return is not None and benchmark_return is not None
                    else None
                ),
                weight=0.0,
            )
        )

        total_cost += cost
        total_value += value
        if benchmark_value is None:
            every_lot_comparable = False
        else:
            total_benchmark_value += benchmark_value

    if not rows:
        return [], None, every_lot_comparable

    rows = [
        row.model_copy(update={"weight": round(row.value / total_value, 4) if total_value else 0.0})
        for row in sorted(rows, key=lambda row: row.return_since_purchase or 0, reverse=True)
    ]
    comparison = PurchaseComparison(
        invested=round(total_cost, 2),
        portfolio_value=round(total_value, 2),
        benchmark_value=round(total_benchmark_value, 2) if every_lot_comparable else None,
        portfolio_return=metrics.round_or_none(total_value / total_cost - 1)
        if total_cost
        else None,
        benchmark_return=metrics.round_or_none(total_benchmark_value / total_cost - 1)
        if every_lot_comparable and total_cost
        else None,
    )
    return rows, comparison, every_lot_comparable


def _concentration_warnings(
    by_holding: list[AllocationSlice], by_sector: list[AllocationSlice]
) -> list[str]:
    warnings: list[str] = []
    if len(by_holding) > 1 and by_holding[0].weight > HOLDING_CONCENTRATION_LIMIT:
        top = by_holding[0]
        warnings.append(
            f"{top.label} makes up {top.weight:.0%} of your portfolio, "
            "so its moves dominate your results."
        )

    named_sectors = [sector for sector in by_sector if sector.label != UNKNOWN_SECTOR]
    if named_sectors and named_sectors[0].weight > SECTOR_CONCENTRATION_LIMIT:
        top = named_sectors[0]
        warnings.append(f"{top.weight:.0%} of your portfolio is in the {top.label} sector.")

    return warnings


async def get_portfolio_analytics(session: AsyncSession, user_id: int) -> PortfolioAnalytics:
    holdings = await portfolio_service.list_raw_holdings(session, user_id)
    empty = PortfolioAnalytics(
        benchmark_symbol=BENCHMARK_SYMBOL, risk_free_rate=metrics.RISK_FREE_RATE
    )
    if not holdings:
        return empty

    symbols = sorted({holding.symbol for holding in holdings})
    # The benchmark may also be one of the holdings, so load it once and keep it in both roles.
    load_symbols = list(dict.fromkeys([*symbols, BENCHMARK_SYMBOL]))
    closes, missing = await _load_closes(load_symbols, HISTORY_PERIOD)
    benchmark = closes.get(BENCHMARK_SYMBOL)
    excluded = [symbol for symbol in missing if symbol in symbols]
    priced_symbols = [symbol for symbol in symbols if symbol in closes]

    warnings: list[str] = []
    if excluded:
        warnings.append(
            f"No price history was available for {', '.join(excluded)}, "
            "so they are left out of this analysis."
        )
    if benchmark is None:
        warnings.append("The S&P 500 benchmark could not be loaded, so comparisons are missing.")
    if not priced_symbols:
        return empty.model_copy(update={"warnings": warnings, "excluded_symbols": excluded})

    quantities: dict[str, float] = defaultdict(float)
    for holding in holdings:
        quantities[holding.symbol] += holding.quantity

    # Risk and the chart describe today's holdings as if held over the last year.
    frame_symbols = [symbol for symbol in load_symbols if symbol in closes]
    window = _aligned_frame(closes, frame_symbols).tail(ANALYSIS_WINDOW_DAYS)
    portfolio_values = sum(window[symbol] * quantities[symbol] for symbol in priced_symbols)
    benchmark_values = window[BENCHMARK_SYMBOL] if benchmark is not None else None

    performance: list[PerformancePoint] = []
    if len(window) >= 2:
        portfolio_index = metrics.rebase_to_100(portfolio_values)
        benchmark_index = (
            metrics.rebase_to_100(benchmark_values) if benchmark_values is not None else None
        )
        performance = [
            PerformancePoint(
                date=day,
                portfolio=round(float(portfolio_index[day]), 2),
                benchmark=round(float(benchmark_index[day]), 2)
                if benchmark_index is not None
                else None,
            )
            for day in window.index
        ]

    rows, since_purchase, every_lot_comparable = _holding_rows(holdings, closes, benchmark)
    if benchmark is not None and not every_lot_comparable:
        warnings.append(
            "Some holdings were bought before the available S&P 500 history starts, "
            "so the since-purchase comparison is incomplete."
        )

    sectors = await _sectors(priced_symbols)
    value_by_sector: dict[str, float] = defaultdict(float)
    for row in rows:
        value_by_sector[sectors[row.symbol]] += row.value

    by_holding = _slices({row.symbol: row.value for row in rows})
    by_sector = _slices(value_by_sector)
    warnings.extend(_concentration_warnings(by_holding, by_sector))

    return PortfolioAnalytics(
        as_of=window.index[-1] if len(window) else None,
        benchmark_symbol=BENCHMARK_SYMBOL,
        risk_free_rate=metrics.RISK_FREE_RATE,
        window_start=window.index[0] if len(window) else None,
        window_end=window.index[-1] if len(window) else None,
        performance=performance,
        portfolio=_risk_metrics(portfolio_values) if len(window) >= 2 else RiskMetrics(),
        benchmark=_risk_metrics(benchmark_values)
        if benchmark_values is not None and len(window) >= 2
        else RiskMetrics(),
        beta=metrics.round_or_none(
            metrics.beta(
                metrics.daily_returns(portfolio_values), metrics.daily_returns(benchmark_values)
            ),
            2,
        )
        if benchmark_values is not None and len(window) >= 2
        else None,
        since_purchase=since_purchase,
        allocation_by_holding=by_holding,
        allocation_by_sector=by_sector,
        holdings=rows,
        warnings=warnings,
        excluded_symbols=excluded,
    )


def normalize_compare_symbols(raw_symbols: str) -> list[str]:
    symbols = list(
        dict.fromkeys(
            stock_service.normalize_ticker(symbol)
            for symbol in raw_symbols.split(",")
            if symbol.strip()
        )
    )
    if not MIN_COMPARE_SYMBOLS <= len(symbols) <= MAX_COMPARE_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Choose between {MIN_COMPARE_SYMBOLS} and {MAX_COMPARE_SYMBOLS} "
                "different stocks to compare."
            ),
        )

    return symbols


async def compare_stocks(symbols: list[str], period: str) -> StockComparison:
    closes, missing = await _load_closes(symbols, period)
    found = [symbol for symbol in symbols if symbol in closes]
    if len(found) < MIN_COMPARE_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Price history was not found for {', '.join(missing)}. "
                "At least two stocks with price history are needed."
            ),
        )

    frame = _aligned_frame(closes, found)
    if len(frame) < 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="These stocks have no trading days in common over this period.",
        )

    rebased = frame.apply(metrics.rebase_to_100)
    points: list[dict[str, float | str]] = [
        {"date": day, **{symbol: round(float(rebased.at[day, symbol]), 2) for symbol in found}}
        for day in rebased.index
    ]

    details = await asyncio.gather(
        *(stock_service.get_stock_detail(symbol) for symbol in found), return_exceptions=True
    )
    stats: list[ComparisonStats] = []
    for symbol, detail in zip(found, details, strict=True):
        risk = _risk_metrics(frame[symbol])
        known = not isinstance(detail, BaseException)
        stats.append(
            ComparisonStats(
                symbol=symbol,
                company_name=detail.company_name if known else None,
                current_price=round(float(frame[symbol].iloc[-1]), 2),
                market_cap=detail.market_cap if known else None,
                pe_ratio=detail.pe_ratio if known else None,
                total_return=risk.total_return,
                volatility=risk.volatility,
                sharpe_ratio=risk.sharpe_ratio,
                max_drawdown=risk.max_drawdown,
            )
        )

    correlation = metrics.correlation_matrix(frame)
    return StockComparison(
        range=period,
        symbols=found,
        window_start=frame.index[0],
        window_end=frame.index[-1],
        points=points,
        stats=stats,
        correlation=CorrelationMatrix(
            symbols=found,
            values=[
                [metrics.round_or_none(correlation.at[row, column], 2) for column in found]
                for row in found
            ],
        ),
        missing_symbols=missing,
    )
