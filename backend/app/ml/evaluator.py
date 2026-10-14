from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class EvaluationMetrics:
    """Out-of-sample metrics for next-day predictions, compared with simple baselines.

    Price errors are in currency units. Returns and accuracies are percentages.
    The naive baseline predicts that tomorrow's close equals today's close; the
    direction baseline always predicts the more common direction in the test set.
    """

    test_days: int
    mae: float
    rmse: float
    mape: float
    baseline_mae: float
    skill_score: float
    direction_accuracy: float
    baseline_direction_accuracy: float
    strategy_return: float
    buy_and_hold_return: float
    strategy_sharpe: float
    buy_and_hold_sharpe: float
    residual_std: float

    def as_dict(self) -> dict[str, float]:
        return {key: float(value) for key, value in asdict(self).items()}


def _total_return_percent(daily_returns: np.ndarray) -> float:
    return float((np.prod(1 + daily_returns) - 1) * 100)


def _annualized_sharpe(daily_returns: np.ndarray) -> float:
    volatility = np.std(daily_returns)
    if volatility == 0:
        return 0.0

    return float(np.mean(daily_returns) / volatility * np.sqrt(TRADING_DAYS_PER_YEAR))


def evaluate_predictions(
    latest_closes: np.ndarray,
    actual_returns: np.ndarray,
    predicted_returns: np.ndarray,
) -> EvaluationMetrics:
    latest_closes = np.asarray(latest_closes, dtype=float)
    actual_returns = np.asarray(actual_returns, dtype=float)
    predicted_returns = np.asarray(predicted_returns, dtype=float)

    actual_closes = latest_closes * (1 + actual_returns)
    predicted_closes = latest_closes * (1 + predicted_returns)
    errors = actual_closes - predicted_closes
    naive_errors = actual_closes - latest_closes

    mae = float(np.mean(np.abs(errors)))
    baseline_mae = float(np.mean(np.abs(naive_errors)))
    skill_score = (1 - mae / baseline_mae) * 100 if baseline_mae > 0 else 0.0

    moved = actual_returns != 0
    actual_up = actual_returns[moved] > 0
    predicted_up = predicted_returns[moved] > 0
    direction_accuracy = float(np.mean(actual_up == predicted_up) * 100) if moved.any() else 0.0
    up_share = float(np.mean(actual_up)) if moved.any() else 0.5
    baseline_direction_accuracy = max(up_share, 1 - up_share) * 100

    # Long when the model expects a gain, otherwise in cash. No costs or slippage.
    strategy_returns = np.where(predicted_returns > 0, actual_returns, 0.0)

    return EvaluationMetrics(
        test_days=len(actual_returns),
        mae=mae,
        rmse=float(np.sqrt(np.mean(np.square(errors)))),
        mape=float(np.mean(np.abs(errors / actual_closes))),
        baseline_mae=baseline_mae,
        skill_score=float(skill_score),
        direction_accuracy=direction_accuracy,
        baseline_direction_accuracy=baseline_direction_accuracy,
        strategy_return=_total_return_percent(strategy_returns),
        buy_and_hold_return=_total_return_percent(actual_returns),
        strategy_sharpe=_annualized_sharpe(strategy_returns),
        buy_and_hold_sharpe=_annualized_sharpe(actual_returns),
        residual_std=float(np.std(actual_returns - predicted_returns)),
    )
