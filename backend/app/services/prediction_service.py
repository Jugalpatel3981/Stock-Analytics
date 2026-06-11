import asyncio

import yfinance as yf
from fastapi import HTTPException, status

from app.schemas.stock import StockPredictionResponse
from app.services.stock_service import normalize_ticker

FEATURE_COLUMNS = [
    "close_lag_1",
    "close_lag_2",
    "volume",
    "ma_5",
    "ma_10",
    "ma_20",
    "daily_return",
    "range_percent",
]


def _build_stock_prediction(ticker: str) -> StockPredictionResponse:
    try:
        import numpy as np
        import pandas as pd
        from xgboost import XGBRegressor
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction dependencies are not installed. Rebuild the backend environment.",
        ) from exc

    normalized_ticker = normalize_ticker(ticker)
    history = yf.Ticker(normalized_ticker).history(period="2y", interval="1d", auto_adjust=False)

    if history.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical prices for '{normalized_ticker}' were not found",
        )

    frame = pd.DataFrame(history).copy()
    frame["close_lag_1"] = frame["Close"].shift(1)
    frame["close_lag_2"] = frame["Close"].shift(2)
    frame["ma_5"] = frame["Close"].rolling(window=5).mean()
    frame["ma_10"] = frame["Close"].rolling(window=10).mean()
    frame["ma_20"] = frame["Close"].rolling(window=20).mean()
    frame["daily_return"] = frame["Close"].pct_change()
    frame["range_percent"] = (frame["High"] - frame["Low"]) / frame["Close"]
    frame["target_next_close"] = frame["Close"].shift(-1)
    frame = frame.rename(columns={"Volume": "volume"}).dropna()

    if len(frame) < 80:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least 80 usable daily price rows are required for prediction.",
        )

    split_index = int(len(frame) * 0.8)
    train_frame = frame.iloc[:split_index]
    test_frame = frame.iloc[split_index:]

    try:
        model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=160,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        model.fit(train_frame[FEATURE_COLUMNS], train_frame["target_next_close"])

        predictions = model.predict(test_frame[FEATURE_COLUMNS])
        actuals = test_frame["target_next_close"].to_numpy()
        mape = np.mean(np.abs((actuals - predictions) / actuals))
        historical_accuracy = max(0.0, min(100.0, (1 - float(mape)) * 100))

        residuals = np.abs(actuals - predictions)
        average_residual_percent = float(np.mean(residuals / actuals))
        confidence_score = max(0.0, min(100.0, (1 - average_residual_percent) * 100))

        final_model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=160,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        final_model.fit(frame[FEATURE_COLUMNS], frame["target_next_close"])

        latest_features = frame[FEATURE_COLUMNS].iloc[[-1]]
        predicted_close = float(final_model.predict(latest_features)[0])
        latest_close = float(frame["Close"].iloc[-1])
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction dependencies are incomplete. Rebuild the backend environment.",
        ) from exc

    return StockPredictionResponse(
        ticker=normalized_ticker,
        predicted_close=round(predicted_close, 2),
        latest_close=round(latest_close, 2),
        confidence_score=round(confidence_score, 2),
        historical_accuracy=round(historical_accuracy, 2),
        training_rows=len(frame),
        feature_summary=[
            "Historical close prices",
            "Trading volume",
            "5-day moving average",
            "10-day moving average",
            "20-day moving average",
            "Daily return",
            "Intraday range percent",
        ],
    )


async def get_stock_prediction(ticker: str) -> StockPredictionResponse:
    return await asyncio.to_thread(_build_stock_prediction, ticker)
