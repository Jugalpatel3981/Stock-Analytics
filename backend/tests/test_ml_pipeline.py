from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from app.ml.evaluator import evaluate_predictions
from app.ml.feature_engineering import FEATURE_COLUMNS, build_feature_set, explain_latest_indicators


@dataclass
class PriceRow:
    price_date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int


def _price_rows(count: int = 90) -> list[PriceRow]:
    start = date(2024, 1, 1)
    rows = []
    for index in range(count):
        close = 100 + index * 0.8
        rows.append(
            PriceRow(
                price_date=start + timedelta(days=index),
                open=close - 0.5,
                high=close + 1.2,
                low=close - 1.4,
                close=close,
                adjusted_close=close,
                volume=1_000_000 + index * 1_000,
            )
        )
    return rows


def test_feature_engineering_generates_shared_feature_set() -> None:
    feature_set = build_feature_set(_price_rows())

    assert not feature_set.supervised_frame.empty
    assert not feature_set.latest_features.empty
    assert set(FEATURE_COLUMNS).issubset(feature_set.frame.columns)
    assert "target_next_close" in feature_set.frame.columns


def test_indicator_explanations_use_available_features() -> None:
    explanations = explain_latest_indicators(_price_rows())

    assert explanations
    assert any("momentum" in explanation.lower() for explanation in explanations)


def test_evaluator_calculates_training_metrics() -> None:
    feature_set = build_feature_set(_price_rows())
    frame = feature_set.supervised_frame.tail(5)
    actuals = frame["target_next_close"].to_numpy(dtype=float)
    predictions = actuals + np.array([0.2, -0.1, 0.3, -0.2, 0.1])

    metrics = evaluate_predictions(frame, actuals, predictions)

    assert metrics.mae > 0
    assert metrics.rmse > 0
    assert 0 <= metrics.mape < 1
    assert 0 <= metrics.direction_accuracy <= 100


def test_training_queue_deduplicates_symbols() -> None:
    from app.ml import training_queue

    training_queue.mark_training_symbol_complete("AMD")

    assert training_queue.enqueue_training_symbol("amd") is True
    assert training_queue.enqueue_training_symbol("AMD") is False
    assert training_queue.is_training_symbol_queued("AMD") is True

    queue = training_queue.get_training_queue()
    while not queue.empty():
        queue.get_nowait()
        queue.task_done()

    training_queue.mark_training_symbol_complete("AMD")
    assert training_queue.is_training_symbol_queued("AMD") is False
