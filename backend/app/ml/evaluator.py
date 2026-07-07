from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EvaluationMetrics:
    mae: float
    rmse: float
    mape: float
    direction_accuracy: float

    @property
    def confidence_score(self) -> float:
        return max(0.0, min(100.0, (1 - self.mape) * 100))


def evaluate_predictions(frame: pd.DataFrame, actuals: np.ndarray, predictions: np.ndarray) -> EvaluationMetrics:
    errors = actuals - predictions
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    safe_actuals = np.where(actuals == 0, np.nan, actuals)
    mape = float(np.nanmean(np.abs(errors / safe_actuals)))

    current_close = frame["close"].to_numpy(dtype=float)
    actual_direction = np.sign(actuals - current_close)
    predicted_direction = np.sign(predictions - current_close)
    direction_accuracy = float(np.mean(actual_direction == predicted_direction) * 100)

    return EvaluationMetrics(
        mae=mae,
        rmse=rmse,
        mape=max(0.0, mape),
        direction_accuracy=max(0.0, min(100.0, direction_accuracy)),
    )
