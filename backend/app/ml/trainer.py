from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ml import registry
from app.ml.data_collector import load_price_history, update_historical_data
from app.ml.evaluator import EvaluationMetrics, evaluate_predictions
from app.ml.feature_engineering import FEATURE_COLUMNS, TARGET_COLUMN, build_feature_set
from app.models.ml import MLTrainingRun
from app.services.stock_service import normalize_ticker


@dataclass(frozen=True)
class CandidateModel:
    model: object
    metrics: EvaluationMetrics
    dataset_size: int


def _fit_xgboost_candidate(price_rows: list[object], min_training_rows: int) -> CandidateModel:
    try:
        from xgboost import XGBRegressor
    except ImportError as exc:
        raise RuntimeError("XGBoost is not installed in the backend environment.") from exc

    feature_set = build_feature_set(price_rows)
    supervised_frame = feature_set.supervised_frame

    if len(supervised_frame) < min_training_rows:
        raise ValueError(
            f"At least {min_training_rows} usable daily price rows are required for model training."
        )

    split_index = int(len(supervised_frame) * 0.8)
    train_frame = supervised_frame.iloc[:split_index]
    test_frame = supervised_frame.iloc[split_index:]

    if train_frame.empty or test_frame.empty:
        raise ValueError("Training split did not produce enough train/test rows.")

    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=220,
        max_depth=3,
        learning_rate=0.045,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    model.fit(train_frame[FEATURE_COLUMNS], train_frame[TARGET_COLUMN])

    predictions = model.predict(test_frame[FEATURE_COLUMNS])
    actuals = test_frame[TARGET_COLUMN].to_numpy(dtype=float)
    metrics = evaluate_predictions(test_frame, actuals, predictions)

    final_model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=220,
        max_depth=3,
        learning_rate=0.045,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
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
            _fit_xgboost_candidate, price_rows, settings.ml_min_training_rows
        )
        version = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        model_path = await registry.save_model_artifact(normalized_ticker, version, candidate.model)

        metrics_payload = {
            "mae": candidate.metrics.mae,
            "rmse": candidate.metrics.rmse,
            "mape": candidate.metrics.mape,
            "direction_accuracy": candidate.metrics.direction_accuracy,
        }
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
