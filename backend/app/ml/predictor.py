from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import registry
from app.ml.data_collector import load_price_history
from app.ml.feature_engineering import FEATURE_COLUMNS, build_feature_set, explain_latest_indicators
from app.ml.training_queue import enqueue_training_symbol
from app.schemas.stock import StockPredictionResponse
from app.services import stock_service
from app.services.stock_service import normalize_ticker


def _expected_range(
    predicted_close: float, latest_close: float, metrics: dict[str, float]
) -> tuple[float, float]:
    mae = metrics.get("mae")
    mape = metrics.get("mape")
    if mae is None and mape is None:
        spread = max(predicted_close * 0.03, 0.01)
    else:
        spread = max(mae or 0, latest_close * (mape or 0), 0.01)

    return predicted_close - spread, predicted_close + spread


def _confidence_score(metrics: dict[str, float]) -> float:
    mape = metrics.get("mape")
    if mape is None:
        return 50.0

    return max(0.0, min(100.0, (1 - mape) * 100))


async def get_stock_prediction(session: AsyncSession, ticker: str) -> StockPredictionResponse:
    normalized_ticker = normalize_ticker(ticker)
    model_record = await registry.get_production_model_record(session, normalized_ticker)
    if model_record is None or not registry.model_artifact_exists(model_record):
        await stock_service.get_stock_detail(normalized_ticker)
        was_enqueued = enqueue_training_symbol(normalized_ticker)
        queue_message = (
            "Model training has been queued."
            if was_enqueued
            else "Model training is already queued."
        )
        return StockPredictionResponse(
            ticker=normalized_ticker,
            status="preparing",
            message=(
                f"Prediction model for {normalized_ticker} is being prepared in the background. "
                f"{queue_message} Please check again shortly."
            ),
            prediction_timestamp=datetime.now(UTC).isoformat(),
        )

    price_rows = await load_price_history(session, normalized_ticker)
    feature_set = build_feature_set(price_rows)
    if feature_set.latest_features.empty:
        was_enqueued = enqueue_training_symbol(normalized_ticker)
        queue_message = (
            "Model refresh has been queued." if was_enqueued else "Model refresh is already queued."
        )
        return StockPredictionResponse(
            ticker=normalized_ticker,
            status="preparing",
            message=(
                f"Latest prediction features for {normalized_ticker} are not ready yet. "
                f"{queue_message} Please check again shortly."
            ),
            prediction_timestamp=datetime.now(UTC).isoformat(),
        )

    model = await registry.load_model_artifact(model_record.model_path)
    latest_features = feature_set.latest_features[FEATURE_COLUMNS].iloc[[-1]]
    predicted_close = float(model.predict(latest_features)[0])
    latest_close = float(feature_set.latest_features["close"].iloc[-1])
    metrics = registry.parse_metrics(model_record)
    expected_low, expected_high = _expected_range(predicted_close, latest_close, metrics)

    return StockPredictionResponse(
        ticker=normalized_ticker,
        predicted_close=round(predicted_close, 2),
        latest_close=round(latest_close, 2),
        expected_price_low=round(expected_low, 2),
        expected_price_high=round(expected_high, 2),
        confidence_score=round(_confidence_score(metrics), 2),
        prediction_timestamp=datetime.now(UTC).isoformat(),
    )


async def build_prediction_context(session: AsyncSession, ticker: str) -> str:
    normalized_ticker = normalize_ticker(ticker)
    try:
        prediction = await get_stock_prediction(session, normalized_ticker)
    except HTTPException as exc:
        return f"Prediction context for {normalized_ticker} unavailable: {exc.detail}"

    price_rows = await load_price_history(session, normalized_ticker)
    indicators = explain_latest_indicators(price_rows)
    indicator_lines = (
        "\n".join(f"- {item}" for item in indicators)
        if indicators
        else "- No strong indicator explanation available."
    )
    if (
        prediction.status == "preparing"
        or prediction.predicted_close is None
        or prediction.latest_close is None
    ):
        return prediction.message or f"Prediction model for {normalized_ticker} is being prepared."

    direction = "higher" if prediction.predicted_close > prediction.latest_close else "lower"

    return "\n".join(
        [
            f"Prediction for {normalized_ticker}: {prediction.predicted_close}",
            f"Latest close: {prediction.latest_close}",
            f"Expected range: {prediction.expected_price_low} to {prediction.expected_price_high}",
            f"Model direction: {direction} than latest close",
            f"Confidence score: {prediction.confidence_score}",
            "Available indicator evidence:",
            indicator_lines,
            "Use these indicators only as evidence. Do not fabricate additional model reasoning.",
        ]
    )
