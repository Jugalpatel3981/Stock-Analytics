"use client";

import { ArrowDownRight, ArrowRight, ArrowUpRight, Clock, Hourglass, Search } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast-provider";
import { getStockPrediction, type PredictionBacktest, type StockPrediction } from "@/lib/api";
import { cn } from "@/lib/utils";

type ReadyStockPrediction = StockPrediction & {
  status: "ready";
  predicted_close: number;
  latest_close: number;
  expected_price_low: number;
  expected_price_high: number;
  predicted_return_percent: number;
  direction: "up" | "down" | "flat";
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Just now";
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return "Just now";
  }

  return parsedDate.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function isReadyPrediction(prediction: StockPrediction): prediction is ReadyStockPrediction {
  return (
    prediction.status === "ready" &&
    prediction.predicted_close !== null &&
    prediction.latest_close !== null &&
    prediction.expected_price_low !== null &&
    prediction.expected_price_high !== null &&
    prediction.predicted_return_percent !== null &&
    prediction.direction !== null
  );
}

function formatPercent(value: number, digits = 1) {
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

const directionStyles = {
  up: { icon: ArrowUpRight, className: "bg-emerald-500/15 text-emerald-400" },
  down: { icon: ArrowDownRight, className: "bg-red-500/15 text-red-400" },
  flat: { icon: ArrowRight, className: "bg-secondary text-secondary-foreground" },
} as const;

function BacktestRow({ label, model, baseline }: { label: string; model: string; baseline: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span>
        <span className="font-semibold">{model}</span>
        <span className="text-muted-foreground"> vs {baseline}</span>
      </span>
    </div>
  );
}

function BacktestSummary({ backtest }: { backtest: PredictionBacktest }) {
  const beatsNaive = backtest.skill_score > 0;

  return (
    <div className="rounded-md border bg-background/40 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-xs font-medium uppercase text-muted-foreground">Track record</p>
        <p className="text-xs text-muted-foreground">
          Walk-forward backtest, {backtest.test_days} unseen trading days
        </p>
      </div>
      <div className="mt-2 divide-y divide-border">
        <BacktestRow
          label="Direction accuracy"
          model={`${backtest.direction_accuracy.toFixed(1)}%`}
          baseline={`${backtest.baseline_direction_accuracy.toFixed(1)}% baseline`}
        />
        <BacktestRow
          label="Avg. price error"
          model={formatCurrency(backtest.mae)}
          baseline={`${formatCurrency(backtest.baseline_mae)} "no change"`}
        />
        <BacktestRow
          label="Strategy return"
          model={formatPercent(backtest.strategy_return)}
          baseline={`${formatPercent(backtest.buy_and_hold_return)} buy & hold`}
        />
      </div>
      <p className={cn("mt-3 text-xs leading-5", beatsNaive ? "text-emerald-400" : "text-muted-foreground")}>
        {beatsNaive
          ? `Beats the "no change" forecast by ${backtest.skill_score.toFixed(1)}%.`
          : `Does not beat the "no change" forecast (${formatPercent(backtest.skill_score)}).`}{" "}
        <span className="text-muted-foreground">Next-day moves are mostly noise, so treat this as weak evidence.</span>
      </p>
    </div>
  );
}

function PredictionDirectionBadge({ prediction }: { prediction: ReadyStockPrediction }) {
  const { icon: Icon, className } = directionStyles[prediction.direction];

  return (
    <div className={cn("flex items-center gap-1 rounded-md px-2.5 py-1.5 text-sm font-semibold", className)}>
      <Icon className="h-4 w-4" aria-hidden="true" />
      {formatPercent(prediction.predicted_return_percent, 2)}
    </div>
  );
}

export function StockPredictionCard() {
  const [ticker, setTicker] = useState("NVDA");
  const [prediction, setPrediction] = useState<StockPrediction | null>(null);
  const { showToast } = useToast();
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);

    try {
      const result = await getStockPrediction(ticker.trim().toUpperCase());
      setPrediction(result);
    } catch (caughtError) {
      setPrediction(null);
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to generate prediction" });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <form className="flex gap-2" onSubmit={handleSubmit}>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <Input
            className="pl-9 uppercase"
            maxLength={12}
            onChange={(event) => setTicker(event.target.value)}
            placeholder="Ticker"
            required
            value={ticker}
          />
        </div>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Loading..." : "Predict"}
        </Button>
      </form>

      {prediction && isReadyPrediction(prediction) ? (
        <div className="space-y-4">
          <div className="rounded-md border bg-background/40 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase text-muted-foreground">{prediction.ticker}</p>
                <p className="mt-2 text-3xl font-semibold tracking-normal">
                  {formatCurrency(prediction.predicted_close)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{prediction.prediction_horizon}</p>
              </div>
              <PredictionDirectionBadge prediction={prediction} />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-md border bg-background/40 p-3">
              <p className="text-xs uppercase text-muted-foreground">Latest Daily Close</p>
              <p className="mt-2 text-sm font-semibold">{formatCurrency(prediction.latest_close)}</p>
            </div>
            <div className="rounded-md border bg-background/40 p-3">
              <p className="text-xs uppercase text-muted-foreground">Typical Range</p>
              <p className="mt-2 text-sm font-semibold">
                {formatCurrency(prediction.expected_price_low)} - {formatCurrency(prediction.expected_price_high)}
              </p>
            </div>
          </div>

          {prediction.backtest ? <BacktestSummary backtest={prediction.backtest} /> : null}

          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">Production model</Badge>
            <Badge variant="outline" className="gap-1">
              <Clock className="h-3.5 w-3.5" aria-hidden="true" />
              {formatTimestamp(prediction.prediction_timestamp)}
            </Badge>
          </div>
        </div>
      ) : prediction?.status === "preparing" ? (
        <div className="rounded-md border bg-background/40 p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
              <Hourglass className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold">Preparing model for {prediction.ticker}</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {prediction.message ?? "The prediction model is being trained in the background. Please check again shortly."}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-md border bg-background/40 p-4 text-sm leading-6 text-muted-foreground">
          Predicts the next trading day&apos;s return with an XGBoost model trained on technical indicators, and shows how the model performed on past data it never saw.
        </div>
      )}
    </div>
  );
}

