from __future__ import annotations

import asyncio
import io
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from joblib import dump, load
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml import MLModel
from app.services.stock_service import normalize_ticker

# Bump when features or the prediction target change so older artifacts are ignored.
MODEL_TYPE = "xgboost-return-v2"
# A retrained model sees newer data, so it replaces production unless its skill
# score is clearly worse than the current model's.
PROMOTION_TOLERANCE = 1.0


def serialize_model(model: Any) -> bytes:
    buffer = io.BytesIO()
    dump(model, buffer)
    return buffer.getvalue()


def deserialize_model(artifact: bytes) -> Any:
    return load(io.BytesIO(artifact))


def artifact_name(ticker: str, version: str) -> str:
    return f"{MODEL_TYPE}/{normalize_ticker(ticker)}/{version}"


async def load_model_artifact(model_record: MLModel) -> Any:
    return await asyncio.to_thread(deserialize_model, model_record.artifact)


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


def is_model_fresh(model_record: MLModel | None, max_age: timedelta) -> bool:
    if not model_artifact_exists(model_record):
        return False

    trained_at = model_record.trained_at
    if trained_at.tzinfo is None:
        trained_at = trained_at.replace(tzinfo=UTC)

    return datetime.now(UTC) - trained_at < max_age


def parse_metrics(model_record: MLModel | None) -> dict[str, float]:
    if model_record is None:
        return {}

    try:
        payload = json.loads(model_record.metrics_json)
    except json.JSONDecodeError:
        return {}

    return {key: float(value) for key, value in payload.items() if isinstance(value, int | float)}


def model_artifact_exists(model_record: MLModel | None) -> bool:
    return model_record is not None and model_record.artifact is not None


def should_promote_model(
    candidate_metrics: dict[str, float], production_record: MLModel | None
) -> bool:
    if production_record is None or not model_artifact_exists(production_record):
        return True

    production_skill = parse_metrics(production_record).get("skill_score")
    candidate_skill = candidate_metrics.get("skill_score")

    if candidate_skill is None:
        return False

    return production_skill is None or candidate_skill >= production_skill - PROMOTION_TOLERANCE


async def register_model(
    session: AsyncSession,
    *,
    ticker: str,
    version: str,
    model_path: str,
    artifact: bytes,
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
        artifact=artifact,
        feature_columns_json=json.dumps(feature_columns),
        metrics_json=json.dumps(metrics),
        is_production=is_production,
        trained_at=datetime.now(UTC),
    )
    session.add(model_record)
    await session.flush()
    return model_record
