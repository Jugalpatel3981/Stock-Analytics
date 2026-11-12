import math

import pandas as pd
import pytest

from app.analytics import metrics


def _series(values: list[float]) -> pd.Series:
    return pd.Series(values, index=[f"2026-01-{day:02d}" for day in range(1, len(values) + 1)])


def test_daily_returns() -> None:
    returns = metrics.daily_returns(_series([100, 110, 99]))

    assert returns.round(4).tolist() == [0.1, -0.1]


def test_total_return() -> None:
    assert metrics.total_return(_series([100, 90, 125])) == pytest.approx(0.25)
    assert metrics.total_return(_series([100])) is None


def test_max_drawdown_is_the_largest_fall_from_a_peak() -> None:
    # Peak 120, then a low of 90: a 25% fall, even though the series ends higher.
    assert metrics.max_drawdown(_series([100, 120, 90, 130])) == pytest.approx(-0.25)


def test_max_drawdown_is_zero_when_prices_only_rise() -> None:
    assert metrics.max_drawdown(_series([100, 101, 105])) == 0


def test_volatility_is_scaled_to_a_year() -> None:
    returns = pd.Series([0.01, -0.01] * 15)

    expected = returns.std(ddof=1) * math.sqrt(252)
    assert metrics.annualized_volatility(returns) == pytest.approx(expected)


def test_risk_figures_need_enough_data() -> None:
    too_short = pd.Series([0.01, -0.01, 0.02])

    assert metrics.annualized_volatility(too_short) is None
    assert metrics.sharpe_ratio(too_short) is None
    assert metrics.beta(too_short, too_short) is None


def test_sharpe_ratio_subtracts_the_risk_free_rate() -> None:
    returns = pd.Series([0.002, 0.0] * 15)

    yearly_return = returns.mean() * 252
    volatility = returns.std(ddof=1) * math.sqrt(252)
    assert metrics.sharpe_ratio(returns, risk_free_rate=0.04) == pytest.approx(
        (yearly_return - 0.04) / volatility
    )


def test_sharpe_ratio_is_none_when_returns_never_change() -> None:
    assert metrics.sharpe_ratio(pd.Series([0.001] * 30)) is None


def test_beta_of_a_series_that_moves_twice_as_much_as_the_benchmark() -> None:
    benchmark = pd.Series([0.01, -0.02, 0.005, 0.015, -0.01] * 6)

    assert metrics.beta(benchmark * 2, benchmark) == pytest.approx(2.0)
    assert metrics.beta(benchmark, benchmark) == pytest.approx(1.0)
    assert metrics.beta(-benchmark, benchmark) == pytest.approx(-1.0)


def test_rebase_to_100() -> None:
    assert metrics.rebase_to_100(_series([50, 55, 45])).tolist() == pytest.approx([100, 110, 90])


def test_correlation_matrix() -> None:
    closes = pd.DataFrame(
        {
            "UP": [100, 102, 101, 105, 104],
            "SAME": [50, 51, 50.5, 52.5, 52],
            "OPPOSITE": [100, 98, 99, 95, 96],
        }
    )

    correlation = metrics.correlation_matrix(closes)

    assert correlation.at["UP", "UP"] == pytest.approx(1.0)
    assert correlation.at["UP", "SAME"] == pytest.approx(1.0)
    assert correlation.at["UP", "OPPOSITE"] < -0.99


def test_round_or_none_hides_values_that_are_not_numbers() -> None:
    assert metrics.round_or_none(0.123456) == 0.1235
    assert metrics.round_or_none(float("nan")) is None
    assert metrics.round_or_none(float("inf")) is None
    assert metrics.round_or_none(None) is None
