"""Walk-forward backtest report for the prediction model.

Usage (from the backend directory):

    python -m app.ml.backtest --symbols AAPL MSFT NVDA --output ../docs/model-performance.md
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime

from app.core.config import get_settings
from app.ml.data_collector import _download_history
from app.ml.evaluator import EvaluationMetrics
from app.ml.feature_engineering import FEATURE_COLUMNS, build_feature_set
from app.ml.trainer import (
    WALK_FORWARD_FOLDS,
    WALK_FORWARD_TEST_SHARE,
    evaluate_walk_forward,
    walk_forward_predictions,
)

METHODOLOGY = f"""\
## Methodology

- **Data:** 5 years of daily prices per ticker from Yahoo Finance.
- **Target:** next trading day's return. The predicted close is the latest close times
  (1 + predicted return).
- **Features:** {len(FEATURE_COLUMNS)} scale-free technical features (returns, moving-average
  gaps, MACD, RSI, Bollinger position, volume ratios, volatility, intraday range, gap).
- **Validation:** expanding-window walk-forward. The most recent
  {int(WALK_FORWARD_TEST_SHARE * 100)}% of days is split into {WALK_FORWARD_FOLDS} consecutive
  folds, and each fold is predicted by a model trained only on earlier days.
- **Baselines:**
  - *Price error:* the naive forecast "tomorrow's close = today's close".
  - *Direction:* always guessing whichever direction was more common in the test period.
- **Strategy:** hold the stock on days the model predicts a gain, otherwise stay in cash.
  No transaction costs or slippage are included.
- **Skill score:** `(1 - model MAE / naive MAE) × 100`. Positive means the model beats the
  naive forecast.
"""

INTERPRETATION = """\
## How to read these results

Next-day stock returns are close to random, so a naive "no change" forecast is very hard
to beat. A skill score near zero and direction accuracy close to the baseline are the
expected outcome for technical-indicator models. Treat any edge here as weak evidence,
not a trading signal. The platform shows these backtest numbers next to every prediction
so users can judge the model for themselves.
"""


def _row(ticker: str, metrics: EvaluationMetrics) -> str:
    return (
        f"| {ticker} | {metrics.test_days} "
        f"| {metrics.direction_accuracy:.1f}% / {metrics.baseline_direction_accuracy:.1f}% "
        f"| {metrics.mae:.2f} / {metrics.baseline_mae:.2f} "
        f"| {metrics.skill_score:+.1f}% "
        f"| {metrics.strategy_return:+.1f}% / {metrics.buy_and_hold_return:+.1f}% "
        f"| {metrics.strategy_sharpe:.2f} / {metrics.buy_and_hold_sharpe:.2f} |"
    )


def evaluate_symbol(ticker: str, period: str) -> EvaluationMetrics:
    rows = _download_history(ticker, period)
    supervised_frame = build_feature_set(rows).supervised_frame
    if len(supervised_frame) < get_settings().ml_min_training_rows:
        raise ValueError(f"only {len(supervised_frame)} usable rows")

    return evaluate_walk_forward(walk_forward_predictions(supervised_frame))


def build_report(results: dict[str, EvaluationMetrics], errors: dict[str, str]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d")
    lines = [
        "# Model Performance",
        "",
        f"Walk-forward backtest generated on {generated} by `python -m app.ml.backtest`.",
        "Each cell shows **model / baseline**.",
        "",
        "| Ticker | Test days | Direction accuracy | Price MAE ($) | Skill vs naive "
        "| Strategy / buy & hold return | Sharpe |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *(_row(ticker, metrics) for ticker, metrics in results.items()),
    ]

    if results:
        count = len(results)
        lines.extend(
            [
                "",
                f"**Average across {count} tickers:** direction accuracy "
                f"{sum(m.direction_accuracy for m in results.values()) / count:.1f}% vs "
                f"{sum(m.baseline_direction_accuracy for m in results.values()) / count:.1f}% "
                f"baseline; skill score "
                f"{sum(m.skill_score for m in results.values()) / count:+.1f}%.",
            ]
        )

    if errors:
        lines.extend(["", "Skipped: " + ", ".join(f"{t} ({e})" for t, e in errors.items())])

    return "\n".join([*lines, "", METHODOLOGY, INTERPRETATION])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--symbols", nargs="+", default=get_settings().default_ml_symbols)
    parser.add_argument("--period", default="5y")
    parser.add_argument("--output", help="Write the Markdown report to this path.")
    args = parser.parse_args()

    results: dict[str, EvaluationMetrics] = {}
    errors: dict[str, str] = {}
    for ticker in args.symbols:
        ticker = ticker.upper()
        try:
            results[ticker] = evaluate_symbol(ticker, args.period)
            print(f"{ticker}: skill {results[ticker].skill_score:+.1f}%")
        except Exception as exc:  # report and keep going with the other tickers
            errors[ticker] = str(exc)
            print(f"{ticker}: skipped ({exc})")

    report = build_report(results, errors)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as report_file:
            report_file.write(report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary_file:
            summary_file.write(report)

    if not results:
        raise SystemExit("No tickers could be evaluated.")


if __name__ == "__main__":
    main()
