"use client";

import { BrainCircuit, Search } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStockPrediction, type StockPrediction } from "@/lib/api";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

export function StockPredictionCard() {
  const [ticker, setTicker] = useState("NVDA");
  const [prediction, setPrediction] = useState<StockPrediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const result = await getStockPrediction(ticker.trim().toUpperCase());
      setPrediction(result);
    } catch (caughtError) {
      setPrediction(null);
      setError(caughtError instanceof Error ? caughtError.message : "Unable to generate prediction");
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
          {isLoading ? "Training..." : "Predict"}
        </Button>
      </form>

      {error ? <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}

      {prediction ? (
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
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <BrainCircuit className="h-5 w-5" aria-hidden="true" />
              </div>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-md border bg-background/40 p-3">
              <p className="text-xs uppercase text-muted-foreground">Latest Close</p>
              <p className="mt-2 text-sm font-semibold">{formatCurrency(prediction.latest_close)}</p>
            </div>
            <div className="rounded-md border bg-background/40 p-3">
              <p className="text-xs uppercase text-muted-foreground">Confidence</p>
              <p className="mt-2 text-sm font-semibold">{prediction.confidence_score.toFixed(2)}%</p>
            </div>
            <div className="rounded-md border bg-background/40 p-3">
              <p className="text-xs uppercase text-muted-foreground">Accuracy</p>
              <p className="mt-2 text-sm font-semibold">{prediction.historical_accuracy.toFixed(2)}%</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{prediction.model_name}</Badge>
            <Badge variant="outline">{prediction.training_rows} rows</Badge>
          </div>
        </div>
      ) : (
        <div className="rounded-md border bg-background/40 p-4 text-sm leading-6 text-muted-foreground">
          Train an XGBoost model from historical prices, volume, and moving averages to estimate the next trading day close.
        </div>
      )}
    </div>
  );
}
