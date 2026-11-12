"use client";

import Link from "next/link";
import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Check, Download, Pencil, Plus, Trash2, Upload, X } from "lucide-react";

import { LiveBadge } from "@/components/market/live-badge";
import { MarketStreamErrorToast } from "@/components/market/market-stream-error-toast";
import { PortfolioGrowthChart } from "@/components/portfolio/portfolio-growth-chart";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast-provider";
import { importPortfolioHoldings, PORTFOLIO_EXPORT_URL, type HoldingImportResult } from "@/lib/analytics-api";
import {
  createPortfolioHolding,
  deletePortfolioHolding,
  getPortfolioGrowth,
  getPortfolioSummary,
  updatePortfolioHolding,
  type PortfolioGrowthPoint,
  type PortfolioHolding,
  type PortfolioSummary,
} from "@/lib/api";
import { useMarketStream } from "@/lib/market-stream";

type PortfolioManagerProps = {
  initialSummary: PortfolioSummary;
  initialGrowth: PortfolioGrowthPoint[];
  reloadOnMount?: boolean;
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

// Today's date in the visitor's own time zone, as YYYY-MM-DD for <input type="date">.
function todayIsoDate() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function formatPercent(value: number | null) {
  if (value === null) {
    return "N/A";
  }

  return `${value.toFixed(2)}%`;
}

export function PortfolioManager({ initialSummary, initialGrowth, reloadOnMount = false }: PortfolioManagerProps) {
  const [summary, setSummary] = useState(initialSummary);
  const [growth, setGrowth] = useState(initialGrowth);
  const { showToast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeDelete, setActiveDelete] = useState<number | null>(null);
  const [editingHoldingId, setEditingHoldingId] = useState<number | null>(null);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const maxBuyDate = todayIsoDate();
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<HoldingImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
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

  const [isReloading, setIsReloading] = useState(reloadOnMount);

  async function refreshPortfolio() {
    // Load holdings and growth independently so a slow price history cannot hide holdings.
    const [summaryResult, growthResult] = await Promise.allSettled([getPortfolioSummary(), getPortfolioGrowth()]);
    if (summaryResult.status === "fulfilled") {
      setSummary(summaryResult.value);
    }
    if (growthResult.status === "fulfilled") {
      setGrowth(growthResult.value.points);
    }
    if (summaryResult.status === "rejected") {
      throw summaryResult.reason;
    }
  }

  useEffect(() => {
    if (!reloadOnMount) {
      return;
    }

    refreshPortfolio()
      .catch(() => showToast({ message: "Portfolio data is taking longer than usual. Please refresh in a moment." }))
      .finally(() => setIsReloading(false));
    // Runs once after a failed server-side load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  async function handleImportFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Clear the input so choosing the same file again still triggers an import.
    event.target.value = "";
    if (!file) {
      return;
    }

    setIsImporting(true);
    setImportResult(null);

    try {
      const result = await importPortfolioHoldings(await file.text());
      setImportResult(result);
      if (result.imported > 0) {
        await refreshPortfolio();
      }
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to import holdings" });
    } finally {
      setIsImporting(false);
    }
  }

  async function handleUpdateHolding(event: FormEvent<HTMLFormElement>, holdingId: number) {
    event.preventDefault();
    setIsSavingEdit(true);

    const formData = new FormData(event.currentTarget);

    try {
      await updatePortfolioHolding(holdingId, {
        quantity: Number(formData.get("quantity")),
        buy_price: Number(formData.get("buy_price")),
        buy_date: String(formData.get("buy_date")),
      });
      await refreshPortfolio();
      setEditingHoldingId(null);
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to update holding" });
    } finally {
      setIsSavingEdit(false);
    }
  }

  async function handleDeleteHolding(holdingId: number, symbol: string) {
    if (!window.confirm(`Remove this ${symbol} holding from your portfolio?`)) {
      return;
    }

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
  // An empty portfolio has nothing to price; only show "Unavailable" when prices are missing.
  const hasPrices = pricedHoldings.length > 0 || liveHoldings.length === 0;
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
      {isReloading ? <p className="text-xs text-muted-foreground">Loading latest portfolio data...</p> : null}
      {unpricedCount > 0 ? (
        <p className="text-xs text-muted-foreground">
          {unpricedCount} of {liveHoldings.length} holdings have no current price yet, so they are left out of the
          value and return totals.
        </p>
      ) : null}

      <section className="rounded-lg border bg-card/80 p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-base font-semibold">Add Holding</h2>
            <p className="mt-1 text-sm text-muted-foreground">Track owned positions with quantity, buy price, and buy date.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              ref={fileInputRef}
              accept=".csv,text/csv"
              aria-label="CSV file of holdings"
              className="hidden"
              onChange={handleImportFile}
              type="file"
            />
            <Button type="button" size="sm" variant="outline" disabled={isImporting} onClick={() => fileInputRef.current?.click()}>
              <Upload className="h-4 w-4" aria-hidden="true" />
              {isImporting ? "Importing..." : "Import CSV"}
            </Button>
            {summary.holdings.length > 0 ? (
              <Button size="sm" variant="outline" asChild>
                <a href={PORTFOLIO_EXPORT_URL} download="portfolio-holdings.csv">
                  <Download className="h-4 w-4" aria-hidden="true" />
                  Export CSV
                </a>
              </Button>
            ) : null}
          </div>
        </div>
        <form className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1fr_auto]" onSubmit={handleCreateHolding}>
          <Input className="uppercase" name="symbol" placeholder="Symbol" maxLength={12} required />
          <Input name="quantity" type="number" step="0.0001" min="0.0001" placeholder="Quantity" required />
          <Input name="buy_price" type="number" step="0.01" min="0.01" placeholder="Buy Price" required />
          <Input name="buy_date" type="date" max={maxBuyDate} aria-label="Buy date" required />
          <Button type="submit" disabled={isSubmitting}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {isSubmitting ? "Adding..." : "Add"}
          </Button>
        </form>
        <p className="mt-3 text-xs text-muted-foreground">
          To add many holdings at once, import a CSV file with the columns symbol, quantity, buy_price and buy_date
          (for example: AAPL, 10, 185.20, 2024-11-04).
        </p>
        {importResult ? (
          <div className="mt-4 rounded-md border bg-background/40 p-4 text-sm" role="status">
            <div className="flex items-start justify-between gap-3">
              <p className="font-medium">
                {importResult.imported === 1 ? "1 holding imported" : `${importResult.imported} holdings imported`}
                {importResult.skipped > 0
                  ? `, ${importResult.skipped} ${importResult.skipped === 1 ? "row" : "rows"} skipped`
                  : ""}
                .
              </p>
              <Button type="button" size="sm" variant="ghost" onClick={() => setImportResult(null)} aria-label="Dismiss import result">
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            {importResult.errors.length > 0 ? (
              <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                {importResult.errors.slice(0, 10).map((error) => (
                  <li key={`${error.row}-${error.message}`}>
                    <span className="font-medium text-foreground">Row {error.row}:</span> {error.message}
                  </li>
                ))}
                {importResult.errors.length > 10 ? <li>and {importResult.errors.length - 10} more.</li> : null}
              </ul>
            ) : null}
          </div>
        ) : null}
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
              <span className="text-right">Actions</span>
            </div>
            {summary.holdings.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">No holdings added yet.</div>
            ) : (
              liveHoldings.map((holding) =>
                editingHoldingId === holding.id ? (
                  <form
                    key={holding.id}
                    className="grid grid-cols-[0.8fr_0.8fr_0.9fr_0.9fr_1fr_1fr_1fr_0.9fr_0.7fr] items-center gap-x-2 border-t bg-secondary/40 px-4 py-3 text-sm"
                    onSubmit={(event) => handleUpdateHolding(event, holding.id)}
                  >
                    <span className="font-semibold text-primary">{holding.symbol}</span>
                    <Input
                      aria-label="Quantity"
                      className="h-9"
                      defaultValue={holding.quantity}
                      min="0.0001"
                      name="quantity"
                      required
                      step="0.0001"
                      type="number"
                    />
                    <Input
                      aria-label="Buy price"
                      className="h-9"
                      defaultValue={holding.buy_price}
                      min="0.01"
                      name="buy_price"
                      required
                      step="0.01"
                      type="number"
                    />
                    <span className="col-span-4 text-xs text-muted-foreground">Change the quantity, buy price or buy date, then save.</span>
                    <Input
                      aria-label="Buy date"
                      className="h-9"
                      defaultValue={holding.buy_date}
                      max={maxBuyDate}
                      name="buy_date"
                      required
                      type="date"
                    />
                    <span className="flex justify-end">
                      <Button type="submit" size="sm" variant="ghost" disabled={isSavingEdit} aria-label="Save changes" title="Save">
                        <Check className="h-4 w-4 text-emerald-400" aria-hidden="true" />
                      </Button>
                      <Button type="button" size="sm" variant="ghost" onClick={() => setEditingHoldingId(null)} aria-label="Cancel" title="Cancel">
                        <X className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </span>
                  </form>
                ) : (
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
                    <span className="flex justify-end">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditingHoldingId(holding.id)}
                        aria-label={`Edit ${holding.symbol} holding`}
                        title="Edit"
                      >
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteHolding(holding.id, holding.symbol)}
                        disabled={activeDelete === holding.id}
                        aria-label={`Remove ${holding.symbol} holding`}
                        title="Remove"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </span>
                  </div>
                ),
              )
            )}
          </div>
        </div>
      </section>
    </div>
  );
}


