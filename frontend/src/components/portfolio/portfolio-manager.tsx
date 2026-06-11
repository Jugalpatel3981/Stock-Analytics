"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { PortfolioGrowthChart } from "@/components/portfolio/portfolio-growth-chart";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createPortfolioHolding,
  deletePortfolioHolding,
  getPortfolioGrowth,
  getPortfolioSummary,
  type PortfolioGrowthPoint,
  type PortfolioSummary,
} from "@/lib/api";

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
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeDelete, setActiveDelete] = useState<number | null>(null);

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
    setError(null);
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
      setError(caughtError instanceof Error ? caughtError.message : "Unable to add holding");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteHolding(holdingId: number) {
    setError(null);
    setActiveDelete(holdingId);

    try {
      await deletePortfolioHolding(holdingId);
      await refreshPortfolio();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to remove holding");
    } finally {
      setActiveDelete(null);
    }
  }

  const statCards = [
    { label: "Current Value", value: formatCurrency(summary.total_value) },
    { label: "Cost Basis", value: formatCurrency(summary.total_cost) },
    { label: "Gain/Loss", value: formatCurrency(summary.total_gain_loss) },
    { label: "Return", value: formatPercent(summary.total_percentage_return) },
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
        {error ? <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}
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
          <h2 className="text-base font-semibold">Holdings Table</h2>
          <p className="mt-1 text-sm text-muted-foreground">Current value, gain/loss, and percentage return.</p>
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
              summary.holdings.map((holding) => (
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
