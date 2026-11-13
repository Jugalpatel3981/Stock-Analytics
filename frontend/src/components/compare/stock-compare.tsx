"use client";

import { Plus, X } from "lucide-react";
import Link from "next/link";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";

import { IndexedLineChart } from "@/components/charts/indexed-line-chart";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PanelSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast-provider";
import { compareStocks, type ComparisonRange, type StockComparison } from "@/lib/analytics-api";
import { searchStocks } from "@/lib/api";
import { divergingColor, seriesColor } from "@/lib/chart-colors";
import {
  changeColor,
  formatCompact,
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
  formatSignedPercent,
} from "@/lib/format";
import { cn } from "@/lib/utils";

const MIN_SYMBOLS = 2;
const MAX_SYMBOLS = 5;

const ranges: Array<{ label: string; value: ComparisonRange }> = [
  { label: "6 Months", value: "6mo" },
  { label: "1 Year", value: "1y" },
  { label: "5 Years", value: "5y" },
];

type StockCompareProps = {
  initialSymbols: string[];
};

function describeCorrelation(value: number) {
  if (value >= 0.7) {
    return "move closely together";
  }
  if (value >= 0.3) {
    return "tend to move together";
  }
  if (value > -0.3) {
    return "move mostly independently";
  }
  return "tend to move in opposite directions";
}

export function StockCompare({ initialSymbols }: StockCompareProps) {
  const [symbols, setSymbols] = useState(initialSymbols);
  const [range, setRange] = useState<ComparisonRange>("1y");
  const [comparison, setComparison] = useState<StockComparison | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { showToast } = useToast();
  const symbolKey = symbols.join(",");

  useEffect(() => {
    const requestedSymbols = symbolKey ? symbolKey.split(",") : [];
    if (requestedSymbols.length < MIN_SYMBOLS) {
      setComparison(null);
      setError(null);
      return;
    }

    let isActive = true;
    setIsLoading(true);
    setError(null);

    compareStocks(requestedSymbols, range)
      .then((result) => {
        if (isActive) {
          setComparison(result);
        }
      })
      .catch((caughtError: unknown) => {
        if (isActive) {
          setComparison(null);
          setError(caughtError instanceof Error ? caughtError.message : "Unable to compare these stocks");
        }
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [range, symbolKey]);

  async function handleAddSymbol(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const query = String(new FormData(form).get("symbol") ?? "").trim();
    if (!query) {
      return;
    }

    if (symbols.length >= MAX_SYMBOLS) {
      showToast({ message: `You can compare up to ${MAX_SYMBOLS} stocks at a time.` });
      return;
    }

    setIsAdding(true);

    try {
      // Accept a company name as well as a ticker by taking the best search match.
      const results = await searchStocks(query);
      const exactMatch = results.find((result) => result.ticker === query.toUpperCase());
      const ticker = (exactMatch ?? results[0])?.ticker;

      if (!ticker) {
        showToast({ message: `No stock found for "${query}".` });
      } else if (symbols.includes(ticker)) {
        showToast({ message: `${ticker} is already in the comparison.` });
      } else {
        setSymbols((current) => [...current, ticker]);
        form.reset();
      }
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to search stocks" });
    } finally {
      setIsAdding(false);
    }
  }

  const correlation = comparison?.correlation ?? null;
  const strongestPair =
    correlation && correlation.symbols.length >= 2
      ? correlation.symbols
          .flatMap((first, row) =>
            correlation.symbols.slice(row + 1).map((second, offset) => ({
              first,
              second,
              value: correlation.values[row][row + 1 + offset],
            })),
          )
          .filter((pair): pair is { first: string; second: string; value: number } => pair.value !== null)
          .sort((left, right) => right.value - left.value)[0]
      : null;

  return (
    <div className="space-y-5">
      <section className="rounded-lg border bg-card/80 p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <ul className="flex flex-wrap gap-2" aria-label="Stocks being compared">
            {symbols.map((symbol, index) => (
              <li key={symbol} className="flex items-center gap-2 rounded-md border bg-background/40 py-1 pl-3 pr-1 text-sm font-medium">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: seriesColor(index) }} aria-hidden="true" />
                {symbol}
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 w-7 p-0"
                  onClick={() => setSymbols((current) => current.filter((item) => item !== symbol))}
                  aria-label={`Remove ${symbol}`}
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
          <form className="flex gap-2" onSubmit={handleAddSymbol}>
            <Input
              aria-label="Add a stock"
              autoComplete="off"
              className="w-full sm:w-64"
              disabled={symbols.length >= MAX_SYMBOLS}
              maxLength={64}
              name="symbol"
              placeholder={symbols.length >= MAX_SYMBOLS ? `Up to ${MAX_SYMBOLS} stocks` : "Add a company or ticker"}
            />
            <Button type="submit" variant="secondary" disabled={isAdding || symbols.length >= MAX_SYMBOLS}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {isAdding ? "Adding..." : "Add"}
            </Button>
          </form>
        </div>
        <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Time period">
          {ranges.map((item) => (
            <Button
              key={item.value}
              type="button"
              size="sm"
              variant={range === item.value ? "default" : "outline"}
              onClick={() => setRange(item.value)}
            >
              {item.label}
            </Button>
          ))}
        </div>
      </section>

      {symbols.length < MIN_SYMBOLS ? (
        <p className="rounded-lg border bg-card/80 p-8 text-center text-sm text-muted-foreground">
          Add at least {MIN_SYMBOLS} stocks to compare them.
        </p>
      ) : error ? (
        <p className="rounded-lg border bg-card/80 p-8 text-center text-sm text-muted-foreground">{error}</p>
      ) : comparison === null ? (
        <div className="space-y-5">
          <PanelSkeleton height="h-80" />
          <PanelSkeleton height="h-48" />
        </div>
      ) : (
        <div className={cn("space-y-5 transition-opacity", isLoading && "opacity-60")}>
          {comparison.missing_symbols.length > 0 ? (
            <p className="rounded-lg border border-amber-400/30 bg-amber-400/5 p-4 text-sm">
              No price history was found for {comparison.missing_symbols.join(", ")}, so it is left out.
            </p>
          ) : null}

          <SectionPanel
            title="Price performance"
            description={`Change since ${formatDate(comparison.window_start)}. Every stock starts at 0%, so different share prices can be compared.`}
          >
            <IndexedLineChart
              points={comparison.points}
              series={comparison.symbols.map((symbol) => ({
                key: symbol,
                label: symbol,
                color: seriesColor(symbols.indexOf(symbol)),
              }))}
            />
          </SectionPanel>

          <SectionPanel
            title="Side by side"
            description={`Return and risk from ${formatDate(comparison.window_start)} to ${formatDate(comparison.window_end)}.`}
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-sm">
                <thead>
                  <tr className="border-b text-left text-xs font-medium uppercase text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Stock</th>
                    <th className="px-4 py-2 text-right font-medium">Price</th>
                    <th className="px-4 py-2 text-right font-medium">Market cap</th>
                    <th className="px-4 py-2 text-right font-medium">P/E</th>
                    <th className="px-4 py-2 text-right font-medium">Return</th>
                    <th className="px-4 py-2 text-right font-medium">Volatility</th>
                    <th className="px-4 py-2 text-right font-medium">Sharpe</th>
                    <th className="py-2 pl-4 text-right font-medium">Max drawdown</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.stats.map((stock) => (
                    <tr key={stock.symbol} className="border-b last:border-b-0">
                      <td className="py-3 pr-4">
                        <Link className="flex items-center gap-2 font-semibold text-primary hover:underline" href={`/stocks/${stock.symbol}`}>
                          <span
                            className="h-2 w-2 rounded-full"
                            style={{ backgroundColor: seriesColor(symbols.indexOf(stock.symbol)) }}
                            aria-hidden="true"
                          />
                          {stock.symbol}
                        </Link>
                        <p className="mt-0.5 text-xs text-muted-foreground">{stock.company_name ?? ""}</p>
                      </td>
                      <td className="px-4 py-3 text-right">{formatCurrency(stock.current_price)}</td>
                      <td className="px-4 py-3 text-right">{formatCompact(stock.market_cap)}</td>
                      <td className="px-4 py-3 text-right">{formatNumber(stock.pe_ratio, 1)}</td>
                      <td className={cn("px-4 py-3 text-right font-medium", changeColor(stock.total_return))}>
                        {formatSignedPercent(stock.total_return)}
                      </td>
                      <td className="px-4 py-3 text-right">{formatPercent(stock.volatility)}</td>
                      <td className="px-4 py-3 text-right">{formatNumber(stock.sharpe_ratio)}</td>
                      <td className="py-3 pl-4 text-right">{formatPercent(stock.max_drawdown)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 text-xs leading-5 text-muted-foreground">
              Volatility is how much the price swings, scaled to a year. The Sharpe ratio is return above a 4% risk-free
              rate per unit of volatility. Max drawdown is the largest fall from a peak.
            </p>
          </SectionPanel>

          {correlation ? (
            <SectionPanel
              title="How the stocks move together"
              description="Correlation of daily returns, from -1 (opposite) through 0 (unrelated) to +1 (identical). Stocks that move together give less diversification."
            >
              <div className="overflow-x-auto">
                <table className="border-separate border-spacing-0.5 text-sm" aria-label="Correlation between stocks">
                  <thead>
                    <tr>
                      <td />
                      {correlation.symbols.map((symbol) => (
                        <th key={symbol} scope="col" className="px-2 pb-1 text-center text-xs font-medium text-muted-foreground">
                          {symbol}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {correlation.symbols.map((rowSymbol, row) => (
                      <tr key={rowSymbol}>
                        <th scope="row" className="pr-3 text-right text-xs font-medium text-muted-foreground">
                          {rowSymbol}
                        </th>
                        {correlation.symbols.map((columnSymbol, column) => {
                          const value = correlation.values[row][column];

                          return (
                            <td
                              key={columnSymbol}
                              className="h-14 w-20 rounded-md text-center font-semibold text-white"
                              style={{ backgroundColor: value === null ? "hsl(var(--secondary))" : divergingColor(value) }}
                              title={
                                value === null
                                  ? `${rowSymbol} and ${columnSymbol}: not enough data`
                                  : `${rowSymbol} and ${columnSymbol}: ${value.toFixed(2)}`
                              }
                            >
                              {value === null ? "N/A" : value.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: divergingColor(-1) }} aria-hidden="true" />
                  -1 opposite
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: divergingColor(0) }} aria-hidden="true" />
                  0 unrelated
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: divergingColor(1) }} aria-hidden="true" />
                  +1 identical
                </span>
              </div>
              {strongestPair ? (
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  <span className="font-medium text-foreground">
                    {strongestPair.first} and {strongestPair.second}
                  </span>{" "}
                  are the most closely linked pair ({strongestPair.value.toFixed(2)}): they {describeCorrelation(strongestPair.value)}.
                </p>
              ) : null}
            </SectionPanel>
          ) : null}

          <p className="rounded-md border bg-card/70 p-4 text-xs leading-5 text-muted-foreground">
            Returns are price returns and do not include dividends. Past performance does not predict future results.
            For informational and educational purposes only.
          </p>
        </div>
      )}
    </div>
  );
}
