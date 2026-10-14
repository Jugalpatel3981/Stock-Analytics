"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { LiveBadge } from "@/components/market/live-badge";
import { MarketStreamErrorToast } from "@/components/market/market-stream-error-toast";
import { PortfolioGrowthChart } from "@/components/portfolio/portfolio-growth-chart";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast-provider";
import {
  createPortfolioHolding,
  deletePortfolioHolding,
  getPortfolioGrowth,
  getPortfolioSummary,
  type PortfolioGrowthPoint,
  type PortfolioHolding,
  type PortfolioSummary,
} from "@/lib/api";
import { useMarketStream } from "@/lib/market-stream";

type PortfolioManagerProps = {
  initialSummary: PortfolioSummary;
  initialGrowth: PortfolioGrowthPoint[];
};

function formatCurrency(value: number | null) {
  if (value === null) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number | null) {
  if (value === null) {
    return "N/A";
  }

  return `${value.toFixed(2)}%`;
}

export function PortfolioManager({ initialSummary, initialGrowth }: PortfolioManagerProps) {
  const [summary, setSummary] = useState(initialSummary);
  const [growth, setGrowth] = useState(initialGrowth);
  const { showToast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeDelete, setActiveDelete] = useState<number | null>(null);
  const trackedSymbols = Array.from(new Set(summary.holdings.map((holding) => holding.symbol)));
  const initialPrices = useMemo(
    () =>
      summary.holdings.reduce<Record<string, number | null>>((prices, holding) => {
        prices[holding.symbol] = holding.current_price;
        return prices;
      }, {}),
    [summary.holdings],
  );
  const { quotes, status, error: streamError, lastUpdated, marketSession, nextMarketOpen, hasExtendedHoursActivity } = useMarketStream(trackedSymbols, { initialPrices });

  async function refreshPortfolio() {
    const [updatedSummary, updatedGrowth] = await Promise.all([
      getPortfolioSummary(),
      getPortfolioGrowth(),
    ]);
    setSummary(updatedSummary);
    setGrowth(updatedGrowth.points);
  }

  async function handleCreateHolding(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);

    const form = event.currentTarget;
    const formData = new FormData(form);

    try {
      await createPortfolioHolding({
        symbol: String(formData.get("symbol") ?? "").trim().toUpperCase(),
        quantity: Number(formData.get("quantity")),
        buy_price: Number(formData.get("buy_price")),
        buy_date: String(formData.get("buy_date")),
      });
      await refreshPortfolio();
      form.reset();
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to add holding" });
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteHolding(holdingId: number) {
    setActiveDelete(holdingId);

    try {
      await deletePortfolioHolding(holdingId);
      await refreshPortfolio();
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to remove holding" });
    } finally {
      setActiveDelete(null);
    }
  }

  const liveHoldings = summary.holdings.map((holding): PortfolioHolding => {
    const livePrice = quotes[holding.symbol]?.price ?? holding.current_price;
    const currentValue = livePrice === null ? holding.current_value : livePrice * holding.quantity;
    const gainLoss = currentValue === null ? holding.gain_loss : currentValue - holding.cost_basis;
    const percentageReturn = gainLoss === null ? holding.percentage_return : (gainLoss / holding.cost_basis) * 100;

    return {
      ...holding,
      current_price: livePrice,
      current_value: currentValue,
      gain_loss: gainLoss,
      percentage_return: percentageReturn,
    };
  });
  // Totals only include holdings with a known price, so a data outage is not shown as a loss.
  const pricedHoldings = liveHoldings.filter((holding) => holding.current_value !== null);
  const unpricedCount = liveHoldings.length - pricedHoldings.length;
  const hasPrices = pricedHoldings.length > 0;
  const liveTotalValue = pricedHoldings.reduce((total, holding) => total + (holding.current_value ?? 0), 0);
  const pricedCost = pricedHoldings.reduce((total, holding) => total + holding.cost_basis, 0);
  const totalCost = liveHoldings.reduce((total, holding) => total + holding.cost_basis, 0);
  const liveTotalGainLoss = liveTotalValue - pricedCost;
  const liveTotalReturn = pricedCost ? (liveTotalGainLoss / pricedCost) * 100 : 0;
  const unavailable = "Unavailable";

  const statCards = [
    { label: "Current Value", value: hasPrices ? formatCurrency(liveTotalValue) : unavailable },
    { label: "Cost Basis", value: formatCurrency(totalCost) },
    { label: "Gain/Loss", value: hasPrices ? formatCurrency(liveTotalGainLoss) : unavailable },
    { label: "Return", value: hasPrices ? formatPercent(liveTotalReturn) : unavailable },
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((card) => (
          <div key={card.label} className="rounded-lg border bg-card/80 p-4">
            <p className="text-xs font-medium uppercase text-muted-foreground">{card.label}</p>
            <p className="mt-3 text-2xl font-semibold tracking-normal">{card.value}</p>
          </div>
        ))}
      </div>
      {unpricedCount > 0 ? (
        <p className="text-xs text-muted-foreground">
          {unpricedCount} of {liveHoldings.length} holdings have no current price yet, so they are left out of the
          value and return totals.
        </p>
      ) : null}

      <section className="rounded-lg border bg-card/80 p-5">
        <div className="mb-4">
          <h2 className="text-base font-semibold">Add Holding</h2>
          <p className="mt-1 text-sm text-muted-foreground">Track owned positions with quantity, buy price, and buy date.</p>
        </div>
        <form className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1fr_auto]" onSubmit={handleCreateHolding}>
          <Input className="uppercase" name="symbol" placeholder="Symbol" maxLength={12} required />
          <Input name="quantity" type="number" step="0.0001" min="0.0001" placeholder="Quantity" required />
          <Input name="buy_price" type="number" step="0.01" min="0.01" placeholder="Buy Price" required />
          <Input name="buy_date" type="date" required />
          <Button type="submit" disabled={isSubmitting}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {isSubmitting ? "Adding..." : "Add"}
          </Button>
        </form>
      </section>

      <section className="rounded-lg border bg-card/80">
        <div className="border-b p-5">
          <h2 className="text-base font-semibold">Portfolio Growth</h2>
          <p className="mt-1 text-sm text-muted-foreground">Historical portfolio value based on closing prices and holdings.</p>
        </div>
        <div className="p-5">
          <PortfolioGrowthChart points={growth} />
        </div>
      </section>

      <section className="rounded-lg border bg-card/80">
        <div className="border-b p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-base font-semibold">Holdings Table</h2>
              <p className="mt-1 text-sm text-muted-foreground">Live value, gain/loss, and percentage return.</p>
            </div>
            <LiveBadge
              status={status}
              lastUpdated={lastUpdated}
              marketSession={marketSession}
              nextMarketOpen={nextMarketOpen}
              hasExtendedHoursActivity={hasExtendedHoursActivity}
            />
          </div>
          <MarketStreamErrorToast error={streamError} />
        </div>
        <div className="overflow-x-auto">
          <div className="min-w-[920px]">
            <div className="grid grid-cols-[0.8fr_0.8fr_0.9fr_0.9fr_1fr_1fr_1fr_0.9fr_0.7fr] bg-secondary px-4 py-3 text-xs font-medium uppercase text-muted-foreground">
              <span>Symbol</span>
              <span>Qty</span>
              <span>Buy Price</span>
              <span>Current</span>
              <span>Current Value</span>
              <span>Gain/Loss</span>
              <span>Return</span>
              <span>Buy Date</span>
              <span className="text-right">Action</span>
            </div>
            {summary.holdings.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">No holdings added yet.</div>
            ) : (
              liveHoldings.map((holding) => (
                <div
                  key={holding.id}
                  className="grid grid-cols-[0.8fr_0.8fr_0.9fr_0.9fr_1fr_1fr_1fr_0.9fr_0.7fr] items-center border-t px-4 py-4 text-sm"
                >
                  <Link className="font-semibold text-primary hover:underline" href={`/stocks/${holding.symbol}`}>
                    {holding.symbol}
                  </Link>
                  <span>{holding.quantity}</span>
                  <span>{formatCurrency(holding.buy_price)}</span>
                  <span>{formatCurrency(holding.current_price)}</span>
                  <span>{formatCurrency(holding.current_value)}</span>
                  <span className={(holding.gain_loss ?? 0) >= 0 ? "font-medium text-emerald-400" : "font-medium text-red-400"}>
                    {formatCurrency(holding.gain_loss)}
                  </span>
                  <span className={(holding.percentage_return ?? 0) >= 0 ? "font-medium text-emerald-400" : "font-medium text-red-400"}>
                    {formatPercent(holding.percentage_return)}
                  </span>
                  <span className="text-muted-foreground">{holding.buy_date}</span>
                  <span className="text-right">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteHolding(holding.id)}
                      disabled={activeDelete === holding.id}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}


