from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ml import registry
from app.ml.data_collector import load_price_history, update_historical_data
from app.ml.evaluator import EvaluationMetrics, evaluate_predictions
from app.ml.feature_engineering import FEATURE_COLUMNS, TARGET_COLUMN, build_feature_set
from app.models.ml import MLTrainingRun
from app.services.stock_service import normalize_ticker

WALK_FORWARD_FOLDS = 5
WALK_FORWARD_TEST_SHARE = 0.4


@dataclass(frozen=True)
class CandidateModel:
    model: object
    metrics: EvaluationMetrics
    dataset_size: int


def _new_regressor() -> object:
    try:
        from xgboost import XGBRegressor
    except ImportError as exc:
        raise RuntimeError("XGBoost is not installed in the backend environment.") from exc

    # Daily returns are mostly noise, so keep the trees shallow and well regularised.
    return XGBRegressor(
        objective="reg:squarederror",
        n_estimators=300,
        max_depth=2,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=10,
        reg_lambda=1.0,
        random_state=42,
    )


def walk_forward_predictions(
    supervised_frame: pd.DataFrame,
    folds: int = WALK_FORWARD_FOLDS,
    test_share: float = WALK_FORWARD_TEST_SHARE,
) -> pd.DataFrame:
    """Out-of-sample predictions from an expanding-window walk-forward split.

    The most recent `test_share` of rows is split into `folds` consecutive blocks.
    Each block is predicted by a model trained only on the rows before it, so no
    prediction ever sees future data.
    """
    test_start = int(len(supervised_frame) * (1 - test_share))
    boundaries = np.linspace(test_start, len(supervised_frame), folds + 1, dtype=int)
    fold_results = []

    for fold_start, fold_end in zip(boundaries[:-1], boundaries[1:], strict=True):
        train_frame = supervised_frame.iloc[:fold_start]
        test_frame = supervised_frame.iloc[fold_start:fold_end]
        if train_frame.empty or test_frame.empty:
            continue

        model = _new_regressor()
        model.fit(train_frame[FEATURE_COLUMNS], train_frame[TARGET_COLUMN])
        fold_results.append(
            pd.DataFrame(
                {
                    "price_date": test_frame["price_date"].to_numpy(),
                    "close": test_frame["close"].to_numpy(dtype=float),
                    "actual_return": test_frame[TARGET_COLUMN].to_numpy(dtype=float),
                    "predicted_return": model.predict(test_frame[FEATURE_COLUMNS]),
                }
            )
        )

    if not fold_results:
        raise ValueError("Walk-forward validation did not produce any test predictions.")

    return pd.concat(fold_results, ignore_index=True)


def evaluate_walk_forward(predictions: pd.DataFrame) -> EvaluationMetrics:
    return evaluate_predictions(
        predictions["close"].to_numpy(),
        predictions["actual_return"].to_numpy(),
        predictions["predicted_return"].to_numpy(),
    )


def fit_candidate(price_rows: list[object], min_training_rows: int) -> CandidateModel:
    supervised_frame = build_feature_set(price_rows).supervised_frame

    if len(supervised_frame) < min_training_rows:
        raise ValueError(
            f"At least {min_training_rows} usable daily price rows are required for training."
        )

    metrics = evaluate_walk_forward(walk_forward_predictions(supervised_frame))

    final_model = _new_regressor()
    final_model.fit(supervised_frame[FEATURE_COLUMNS], supervised_frame[TARGET_COLUMN])

    return CandidateModel(
        model=final_model,
        metrics=metrics,
        dataset_size=len(supervised_frame),
    )


async def train_model_for_ticker(
    session: AsyncSession, ticker: str, *, refresh_data: bool = True
) -> MLTrainingRun:
    settings = get_settings()
    normalized_ticker = normalize_ticker(ticker)
    started_at = datetime.now(UTC)
    timer_start = perf_counter()
    training_run = MLTrainingRun(
        ticker=normalized_ticker,
        model_type=registry.MODEL_TYPE,
        status="running",
        started_at=started_at,
    )
    session.add(training_run)
    await session.commit()
    await session.refresh(training_run)

    try:
        if refresh_data:
            await update_historical_data(session, normalized_ticker)

        price_rows = await load_price_history(session, normalized_ticker)
        candidate = await asyncio.to_thread(
            fit_candidate, price_rows, settings.ml_min_training_rows
        )
        version = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        model_path = await registry.save_model_artifact(normalized_ticker, version, candidate.model)

        metrics_payload = candidate.metrics.as_dict()
        production_record = await registry.get_production_model_record(session, normalized_ticker)
        should_promote = registry.should_promote_model(metrics_payload, production_record)
        await registry.register_model(
            session,
            ticker=normalized_ticker,
            version=version,
            model_path=model_path,
            feature_columns=FEATURE_COLUMNS,
            metrics=metrics_payload,
            is_production=should_promote,
        )

        training_run.status = "completed"
        training_run.dataset_size = candidate.dataset_size
        training_run.mae = candidate.metrics.mae
        training_run.rmse = candidate.metrics.rmse
        training_run.mape = candidate.metrics.mape
        training_run.direction_accuracy = candidate.metrics.direction_accuracy
        training_run.replaced_production_model = should_promote
        training_run.model_path = model_path
    except Exception as exc:
        training_run.status = "failed"
        training_run.error_message = str(exc)
    finally:
        training_run.finished_at = datetime.now(UTC)
        training_run.duration_seconds = perf_counter() - timer_start
        await session.commit()
        await session.refresh(training_run)

    return training_run
