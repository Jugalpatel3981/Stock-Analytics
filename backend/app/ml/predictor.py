from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import registry
from app.ml.data_collector import load_price_history
from app.ml.feature_engineering import FEATURE_COLUMNS, build_feature_set, explain_latest_indicators
from app.ml.training_queue import enqueue_training_symbol
from app.schemas.stock import PredictionBacktest, StockPredictionResponse
from app.services import stock_service
from app.services.stock_service import normalize_ticker


def _expected_range(latest_close: float, predicted_return: float, residual_std: float | None):
    """One standard deviation of the model's out-of-sample return error (~68% of days)."""
    spread = residual_std if residual_std is not None else 0.02
    return (
        latest_close * (1 + predicted_return - spread),
        latest_close * (1 + predicted_return + spread),
    )


def _direction(predicted_return: float) -> str:
    if abs(predicted_return) < 0.0005:
        return "flat"

    return "up" if predicted_return > 0 else "down"


def _backtest(metrics: dict[str, float]) -> PredictionBacktest | None:
    try:
        return PredictionBacktest(
            test_days=int(metrics["test_days"]),
            **{
                field: round(metrics[field], 2)
                for field in PredictionBacktest.model_fields
                if field != "test_days"
            },
        )
    except KeyError:
        return None


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
    predicted_return = float(model.predict(latest_features)[0])
    latest_close = float(feature_set.latest_features["close"].iloc[-1])
    metrics = registry.parse_metrics(model_record)
    expected_low, expected_high = _expected_range(
        latest_close, predicted_return, metrics.get("residual_std")
    )

    return StockPredictionResponse(
        ticker=normalized_ticker,
        predicted_close=round(latest_close * (1 + predicted_return), 2),
        predicted_return_percent=round(predicted_return * 100, 3),
        direction=_direction(predicted_return),
        latest_close=round(latest_close, 2),
        expected_price_low=round(expected_low, 2),
        expected_price_high=round(expected_high, 2),
        backtest=_backtest(metrics),
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

    lines = [
        f"Model prediction for {normalized_ticker}: next close {prediction.predicted_close} "
        f"({prediction.predicted_return_percent:+.2f}%, direction {prediction.direction})",
        f"Latest close: {prediction.latest_close}",
        f"Typical range (one standard deviation of past model error): "
        f"{prediction.expected_price_low} to {prediction.expected_price_high}",
    ]
    if prediction.backtest is not None:
        backtest = prediction.backtest
        lines.extend(
            [
                f"Walk-forward backtest over {backtest.test_days} trading days:",
                f"- Direction accuracy {backtest.direction_accuracy}% vs "
                f"{backtest.baseline_direction_accuracy}% for always guessing the common direction",
                f"- Price error (MAE) {backtest.mae} vs {backtest.baseline_mae} for assuming "
                f"no change (skill score {backtest.skill_score}%)",
            ]
        )

    lines.extend(
        [
            "Available indicator evidence:",
            indicator_lines,
            "Next-day stock moves are mostly noise. Describe the prediction as weak evidence, "
            "quote the backtest honestly, and do not fabricate additional model reasoning.",
        ]
    )
    return "\n".join(lines)
