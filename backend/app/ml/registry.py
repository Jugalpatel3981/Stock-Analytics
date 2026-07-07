from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from joblib import dump, load
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ml import MLModel
from app.services.stock_service import normalize_ticker

MODEL_TYPE = "xgboost"


def get_models_root() -> Path:
    settings = get_settings()
    root = Path(settings.ml_models_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _model_path(ticker: str, version: str) -> Path:
    safe_ticker = normalize_ticker(ticker).replace("/", "-")
    directory = get_models_root() / safe_ticker
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{MODEL_TYPE}-{version}.joblib"


async def save_model_artifact(ticker: str, version: str, model: Any) -> str:
    path = _model_path(ticker, version)
    await asyncio.to_thread(dump, model, path)
    return str(path)


async def load_model_artifact(model_path: str) -> Any:
    return await asyncio.to_thread(load, model_path)


async def get_production_model_record(session: AsyncSession, ticker: str) -> MLModel | None:
    normalized_ticker = normalize_ticker(ticker)
    result = await session.execute(
        select(MLModel)
        .where(
            MLModel.ticker == normalized_ticker,
            MLModel.model_type == MODEL_TYPE,
            MLModel.is_production.is_(True),
        )
        .order_by(MLModel.trained_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def parse_metrics(model_record: MLModel | None) -> dict[str, float]:
    if model_record is None:
        return {}

    try:
        payload = json.loads(model_record.metrics_json)
    except json.JSONDecodeError:
        return {}

    return {key: float(value) for key, value in payload.items() if isinstance(value, int | float)}


def model_artifact_exists(model_record: MLModel | None) -> bool:
    return model_record is not None and Path(model_record.model_path).exists()


def should_promote_model(candidate_metrics: dict[str, float], production_record: MLModel | None) -> bool:
    if production_record is None or not model_artifact_exists(production_record):
        return True

    production_metrics = parse_metrics(production_record)
    production_mape = production_metrics.get("mape")
    candidate_mape = candidate_metrics.get("mape")

    if production_mape is None or candidate_mape is None:
        return False

    return candidate_mape < production_mape


async def register_model(
    session: AsyncSession,
    *,
    ticker: str,
    version: str,
    model_path: str,
    feature_columns: list[str],
    metrics: dict[str, float],
    is_production: bool,
) -> MLModel:
    normalized_ticker = normalize_ticker(ticker)

    if is_production:
        await session.execute(
            update(MLModel)
            .where(MLModel.ticker == normalized_ticker, MLModel.model_type == MODEL_TYPE)
            .values(is_production=False)
        )

    model_record = MLModel(
        ticker=normalized_ticker,
        model_type=MODEL_TYPE,
        version=version,
        model_path=model_path,
        feature_columns_json=json.dumps(feature_columns),
        metrics_json=json.dumps(metrics),
        is_production=is_production,
        trained_at=datetime.now(UTC),
    )
    session.add(model_record)
    await session.flush()
    return model_record


