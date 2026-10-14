from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# Every feature is scale-free (a return, ratio or oscillator) so the model learns
# patterns that transfer across price levels instead of memorising raw prices.
FEATURE_COLUMNS = [
    "return_1",
    "return_2",
    "return_5",
    "return_10",
    "close_to_sma_5",
    "close_to_sma_10",
    "close_to_sma_20",
    "close_to_sma_50",
    "macd_percent",
    "macd_signal_percent",
    "macd_histogram_percent",
    "rsi_14",
    "bollinger_percent",
    "volume_ratio_5",
    "volume_ratio_20",
    "volatility_10",
    "volatility_20",
    "range_percent",
    "gap_percent",
]
TARGET_COLUMN = "target_next_return"


@dataclass(frozen=True)
class FeatureSet:
    frame: pd.DataFrame
    supervised_frame: pd.DataFrame
    latest_features: pd.DataFrame


def _field(row: Any, name: str) -> Any:
    return row.get(name) if isinstance(row, dict) else getattr(row, name, None)


def _to_records_frame(price_rows: list[Any]) -> pd.DataFrame:
    """Accepts ORM rows or plain dicts, such as rows from the backtest script."""
    records = []
    for row in price_rows:
        records.append(
            {
                "price_date": _field(row, "price_date"),
                "open": float(_field(row, "open")),
                "high": float(_field(row, "high")),
                "low": float(_field(row, "low")),
                "close": float(_field(row, "close")),
                "adjusted_close": float(_field(row, "adjusted_close")),
                "volume": float(_field(row, "volume") or 0),
            }
        )

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame

    return frame.sort_values("price_date").reset_index(drop=True)


def _calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + relative_strength))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100)
    rsi = rsi.mask((loss == 0) & (gain == 0), 50)
    return rsi


def build_feature_frame(price_rows: list[Any]) -> pd.DataFrame:
    frame = _to_records_frame(price_rows)
    if frame.empty:
        return frame

    close = frame["close"]
    frame["sma_5"] = close.rolling(window=5).mean()
    frame["sma_10"] = close.rolling(window=10).mean()
    frame["sma_20"] = close.rolling(window=20).mean()
    frame["sma_50"] = close.rolling(window=50).mean()
    frame["ema_12"] = close.ewm(span=12, adjust=False).mean()
    frame["ema_26"] = close.ewm(span=26, adjust=False).mean()
    frame["macd"] = frame["ema_12"] - frame["ema_26"]
    frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False).mean()
    frame["macd_histogram"] = frame["macd"] - frame["macd_signal"]
    frame["rsi_14"] = _calculate_rsi(close, 14)
    bollinger_mid = close.rolling(window=20).mean()
    bollinger_std = close.rolling(window=20).std()
    frame["bollinger_upper"] = bollinger_mid + (2 * bollinger_std)
    frame["bollinger_lower"] = bollinger_mid - (2 * bollinger_std)
    band_width = (frame["bollinger_upper"] - frame["bollinger_lower"]).replace(0, np.nan)
    frame["bollinger_percent"] = (close - frame["bollinger_lower"]) / band_width
    frame["rolling_volume_5"] = frame["volume"].rolling(window=5).mean()
    frame["rolling_volume_20"] = frame["volume"].rolling(window=20).mean()
    frame["momentum_5"] = close - close.shift(5)
    frame["momentum_10"] = close - close.shift(10)
    frame["daily_return"] = close.pct_change()
    frame["volatility_10"] = frame["daily_return"].rolling(window=10).std()
    frame["volatility_20"] = frame["daily_return"].rolling(window=20).std()
    frame["range_percent"] = (frame["high"] - frame["low"]) / close.replace(0, np.nan)

    for days in (1, 2, 5, 10):
        frame[f"return_{days}"] = close.pct_change(days)
    for window in (5, 10, 20, 50):
        frame[f"close_to_sma_{window}"] = close / frame[f"sma_{window}"] - 1
    frame["macd_percent"] = frame["macd"] / close
    frame["macd_signal_percent"] = frame["macd_signal"] / close
    frame["macd_histogram_percent"] = frame["macd_histogram"] / close
    frame["volume_ratio_5"] = frame["volume"] / frame["rolling_volume_5"].replace(0, np.nan)
    frame["volume_ratio_20"] = frame["volume"] / frame["rolling_volume_20"].replace(0, np.nan)
    frame["gap_percent"] = frame["open"] / close.shift(1) - 1

    frame["next_close"] = close.shift(-1)
    frame[TARGET_COLUMN] = frame["next_close"] / close - 1
    frame = frame.replace([np.inf, -np.inf], np.nan)
    return frame


def build_feature_set(price_rows: list[Any]) -> FeatureSet:
    frame = build_feature_frame(price_rows)
    if frame.empty:
        return FeatureSet(frame=frame, supervised_frame=frame, latest_features=frame)

    supervised_frame = frame.dropna(subset=[*FEATURE_COLUMNS, TARGET_COLUMN])
    latest_features = frame.dropna(subset=FEATURE_COLUMNS).tail(1)
    return FeatureSet(
        frame=frame, supervised_frame=supervised_frame, latest_features=latest_features
    )


def explain_latest_indicators(price_rows: list[Any]) -> list[str]:
    feature_set = build_feature_set(price_rows)
    if feature_set.latest_features.empty:
        return []

    latest = feature_set.latest_features.iloc[-1]
    explanations: list[str] = []

    if latest["momentum_5"] > 0:
        explanations.append("Positive 5-day momentum")
    elif latest["momentum_5"] < 0:
        explanations.append("Negative 5-day momentum")

    if latest["macd"] > latest["macd_signal"]:
        explanations.append("MACD is above its signal line")
    elif latest["macd"] < latest["macd_signal"]:
        explanations.append("MACD is below its signal line")

    if latest["rsi_14"] >= 70:
        explanations.append("RSI indicates overbought conditions")
    elif latest["rsi_14"] <= 30:
        explanations.append("RSI indicates oversold conditions")

    if latest["close"] > latest["sma_20"]:
        explanations.append("Price is trading above the 20-day moving average")
    elif latest["close"] < latest["sma_20"]:
        explanations.append("Price is trading below the 20-day moving average")

    if latest["volume"] > latest["rolling_volume_20"]:
        explanations.append("Recent volume is above its 20-day average")

    return explanations[:6]
