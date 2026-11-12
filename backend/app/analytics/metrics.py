"""Risk and return calculations on daily price series.

Every function is pure: it takes numbers in and returns numbers, so the maths can be
tested without market data. Returns are simple price returns and exclude dividends.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252
# Assumed yearly return of a risk-free investment, used by the Sharpe ratio.
RISK_FREE_RATE = 0.04
# A series needs at least this many daily returns before risk figures mean anything.
MIN_RETURNS_FOR_RISK = 20
# Volatility below this is rounding noise from a series that does not really move.
NEGLIGIBLE_VOLATILITY = 1e-9


def daily_returns(values: pd.Series) -> pd.Series:
    """Day-over-day change, as a fraction (0.01 is +1%)."""
    return values.pct_change().dropna()


def total_return(values: pd.Series) -> float | None:
    """Change from the first value to the last, as a fraction."""
    if len(values) < 2 or values.iloc[0] <= 0:
        return None

    return float(values.iloc[-1] / values.iloc[0] - 1)


def annualized_volatility(returns: pd.Series) -> float | None:
    """How much daily returns swing, scaled to a year. Higher means a bumpier ride."""
    if len(returns) < MIN_RETURNS_FOR_RISK:
        return None

    return float(returns.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float | None:
    """Yearly return earned above the risk-free rate, per unit of volatility."""
    volatility = annualized_volatility(returns)
    if volatility is None or volatility < NEGLIGIBLE_VOLATILITY:
        return None

    yearly_return = float(returns.mean() * TRADING_DAYS_PER_YEAR)
    return (yearly_return - risk_free_rate) / volatility


def max_drawdown(values: pd.Series) -> float | None:
    """Largest fall from an earlier peak, as a negative fraction (-0.2 is a 20% fall)."""
    if len(values) < 2:
        return None

    running_peak = values.cummax()
    return float((values / running_peak - 1).min())


def beta(returns: pd.Series, benchmark_returns: pd.Series) -> float | None:
    """Sensitivity to the benchmark: 1.2 means it tends to move 1.2% when the market moves 1%."""
    aligned = pd.concat([returns, benchmark_returns], axis=1, join="inner").dropna()
    if len(aligned) < MIN_RETURNS_FOR_RISK:
        return None

    benchmark_variance = float(aligned.iloc[:, 1].var(ddof=1))
    if benchmark_variance == 0:
        return None

    covariance = float(aligned.iloc[:, 0].cov(aligned.iloc[:, 1]))
    return covariance / benchmark_variance


def rebase_to_100(values: pd.Series) -> pd.Series:
    """Scale a series so it starts at 100, which makes different prices comparable."""
    return values / values.iloc[0] * 100


def correlation_matrix(closes: pd.DataFrame) -> pd.DataFrame:
    """Correlation of daily returns between every pair of columns (-1 to 1)."""
    return closes.pct_change().dropna().corr()


def round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None or not np.isfinite(value):
        return None

    return round(float(value), digits)
