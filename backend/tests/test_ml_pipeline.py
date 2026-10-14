from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pytest

from app.ml import registry
from app.ml.evaluator import evaluate_predictions
from app.ml.feature_engineering import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_feature_set,
    explain_latest_indicators,
)
from app.ml.trainer import fit_candidate, walk_forward_predictions


@dataclass
class PriceRow:
    price_date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int


def _price_rows(count: int = 90, *, scale: float = 1.0, noise_seed: int | None = None):
    start = date(2024, 1, 1)
    noise = (
        np.random.default_rng(noise_seed).normal(0, 0.01, count)
        if noise_seed is not None
        else np.zeros(count)
    )
    rows = []
    for index in range(count):
        close = scale * (100 + index * 0.8) * (1 + noise[index])
        rows.append(
            PriceRow(
                price_date=start + timedelta(days=index),
                open=close * 0.995,
                high=close * 1.012,
                low=close * 0.986,
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
    assert TARGET_COLUMN in feature_set.frame.columns


def test_features_are_scale_free() -> None:
    small = build_feature_set(_price_rows(noise_seed=1)).supervised_frame[FEATURE_COLUMNS]
    large = build_feature_set(_price_rows(scale=50, noise_seed=1)).supervised_frame[FEATURE_COLUMNS]

    np.testing.assert_allclose(small.to_numpy(), large.to_numpy(), rtol=1e-9)


def test_indicator_explanations_use_available_features() -> None:
    explanations = explain_latest_indicators(_price_rows())

    assert explanations
    assert any("momentum" in explanation.lower() for explanation in explanations)


def test_evaluator_compares_against_baselines() -> None:
    closes = np.array([100.0, 101.0, 99.0, 100.0])
    actual_returns = np.array([0.01, -0.02, 0.01, 0.02])
    predicted_returns = np.array([0.005, -0.01, -0.005, 0.01])

    metrics = evaluate_predictions(closes, actual_returns, predicted_returns)

    assert metrics.test_days == 4
    assert metrics.baseline_mae == pytest.approx(np.mean(np.abs(closes * actual_returns)))
    assert metrics.mae < metrics.baseline_mae
    assert metrics.skill_score > 0
    assert metrics.direction_accuracy == 75.0
    assert metrics.baseline_direction_accuracy == 75.0
    # Long only on days 1 and 4, when the model predicted a gain.
    assert metrics.strategy_return == pytest.approx((1.01 * 1.02 - 1) * 100)
    assert metrics.buy_and_hold_return == pytest.approx((1.01 * 0.98 * 1.01 * 1.02 - 1) * 100)


def test_walk_forward_only_predicts_after_training_data() -> None:
    supervised_frame = build_feature_set(_price_rows(300, noise_seed=7)).supervised_frame

    predictions = walk_forward_predictions(supervised_frame, folds=4, test_share=0.4)

    first_test_index = int(len(supervised_frame) * 0.6)
    expected_dates = supervised_frame["price_date"].iloc[first_test_index:].to_numpy()
    assert list(predictions["price_date"]) == list(expected_dates)
    assert predictions["predicted_return"].notna().all()


def test_fit_candidate_reports_walk_forward_metrics() -> None:
    candidate = fit_candidate(_price_rows(300, noise_seed=3), min_training_rows=120)

    assert candidate.dataset_size > 120
    assert candidate.metrics.test_days > 0
    assert candidate.metrics.residual_std > 0
    assert set(candidate.metrics.as_dict()) >= {"skill_score", "baseline_mae", "strategy_return"}


def test_fit_candidate_requires_enough_rows() -> None:
    with pytest.raises(ValueError, match="usable daily price rows"):
        fit_candidate(_price_rows(80), min_training_rows=120)


def test_promotion_keeps_clearly_better_production_model(monkeypatch) -> None:
    monkeypatch.setattr(registry, "model_artifact_exists", lambda _record: True)
    production = type("Record", (), {"metrics_json": '{"skill_score": 5.0}'})()

    assert registry.should_promote_model({"skill_score": 4.5}, production) is True
    assert registry.should_promote_model({"skill_score": 3.0}, production) is False


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


def test_backtest_report_lists_each_ticker(monkeypatch) -> None:
    from app.ml import backtest

    monkeypatch.setattr(
        backtest, "_download_history", lambda _ticker, _period: _price_rows(300, noise_seed=11)
    )

    report = backtest.build_report(
        {"AAPL": backtest.evaluate_symbol("AAPL", "5y")}, {"BAD": "no data"}
    )

    assert "| AAPL |" in report
    assert "Skipped: BAD (no data)" in report
    assert "## Methodology" in report
