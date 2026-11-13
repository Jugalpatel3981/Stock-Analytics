"use client";

import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { IndexedLineChart } from "@/components/charts/indexed-line-chart";
import { Sparkline } from "@/components/dashboard/sparkline";
import { LiveBadge } from "@/components/market/live-badge";
import { MarketStreamErrorToast } from "@/components/market/market-stream-error-toast";
import { Button } from "@/components/ui/button";
import { PanelSkeleton, RowsSkeleton, Skeleton, StatTilesSkeleton } from "@/components/ui/skeleton";
import { getPortfolioAnalytics, type PortfolioAnalytics } from "@/lib/analytics-api";
import { getPortfolioSummary, getStockHistory, getWatchlists, type PortfolioSummary } from "@/lib/api";
import { SERIES_COLORS } from "@/lib/chart-colors";
import { changeColor, formatCurrency, formatSignedPercent } from "@/lib/format";
import { useMarketStream } from "@/lib/market-stream";
import { changeSinceLastClose, summarizeQuote } from "@/lib/quote-display";
import { cn } from "@/lib/utils";

const BENCHMARK = "SPY";
const MAX_WATCHLIST_ROWS = 8;
const MOVERS_PER_SIDE = 3;

const COMPANY_NAMES: Record<string, string> = {
  AAPL: "Apple",
  AMZN: "Amazon",
  GOOGL: "Alphabet",
  JPM: "JPMorgan Chase",
  KO: "Coca-Cola",
  META: "Meta Platforms",
  MSFT: "Microsoft",
  NVDA: "NVIDIA",
  SPY: "S&P 500 ETF",
  TSLA: "Tesla",
};

type DashboardData = {
  summary: PortfolioSummary | null;
  analytics: PortfolioAnalytics | null;
  watchlistSymbols: string[];
};

type StatProps = {
  label: string;
  value: ReactNode;
  detail: ReactNode;
  tone?: number | null;
};

function Stat({ label, value, detail, tone }: StatProps) {
  return (
    <div className="rounded-lg border bg-card/80 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={cn("mt-3 text-2xl font-semibold tracking-tight", tone !== undefined && changeColor(tone))}>{value}</p>
      <p className="mt-2 text-xs leading-5 text-muted-foreground">{detail}</p>
    </div>
  );
}

function ChangeText({ value, suffix = "" }: { value: number | null; suffix?: string }) {
  return <span className={cn("font-medium", changeColor(value))}>{formatSignedPercent(value, 2)}{suffix}</span>;
}

function Panel({ title, description, action, children }: { title: string; description?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="min-w-0 rounded-lg border bg-card/80">
      <div className="flex items-start justify-between gap-4 border-b p-5">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

function useMonthlyCloses(symbols: string[]) {
  const [closes, setCloses] = useState<Record<string, number[]>>({});
  const symbolKey = symbols.join(",");

  useEffect(() => {
    if (!symbolKey) {
      return;
    }

    let isActive = true;
    for (const symbol of symbolKey.split(",")) {
      getStockHistory(symbol, "1mo")
        .then((history) => {
          if (isActive) {
            setCloses((current) => ({ ...current, [symbol]: history.prices.map((point) => point.close) }));
          }
        })
        .catch(() => {
          if (isActive) {
            setCloses((current) => ({ ...current, [symbol]: [] }));
          }
        });
    }

    return () => {
      isActive = false;
    };
  }, [symbolKey]);

  return closes;
}

type DashboardOverviewProps = {
  /** Shown beside the watchlist, such as the news panel. */
  aside: ReactNode;
};

export function DashboardOverview({ aside }: DashboardOverviewProps) {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    let isActive = true;

    // Load each part on its own, so one slow source does not hold back the others.
    Promise.allSettled([getPortfolioSummary(), getPortfolioAnalytics(), getWatchlists()]).then(
      ([summaryResult, analyticsResult, watchlistsResult]) => {
        if (!isActive) {
          return;
        }

        const watchlists = watchlistsResult.status === "fulfilled" ? watchlistsResult.value : [];
        setData({
          summary: summaryResult.status === "fulfilled" ? summaryResult.value : null,
          analytics: analyticsResult.status === "fulfilled" ? analyticsResult.value : null,
          watchlistSymbols: Array.from(
            new Set(watchlists.flatMap((watchlist) => watchlist.stocks.map((stock) => stock.ticker.toUpperCase()))),
          ).slice(0, MAX_WATCHLIST_ROWS),
        });
      },
    );

    return () => {
      isActive = false;
    };
  }, []);

  const holdings = useMemo(() => data?.summary?.holdings ?? [], [data]);
  const holdingSymbols = useMemo(() => Array.from(new Set(holdings.map((holding) => holding.symbol))), [holdings]);
  const watchlistSymbols = useMemo(() => data?.watchlistSymbols ?? [], [data]);
  const streamSymbols = useMemo(
    () => (data ? Array.from(new Set([...holdingSymbols, ...watchlistSymbols, BENCHMARK])) : []),
    [data, holdingSymbols, watchlistSymbols],
  );
  const { quotes, status, error, lastUpdated, marketSession, nextMarketOpen, hasExtendedHoursActivity } =
    useMarketStream(streamSymbols);
  const monthlyCloses = useMonthlyCloses(watchlistSymbols);

  const portfolio = useMemo(() => {
    let value = 0;
    let cost = 0;
    let todayChange = 0;
    let pricedCount = 0;
    let hasTodayChange = false;

    for (const holding of holdings) {
      const quote = quotes[holding.symbol];
      const price = summarizeQuote(quote).price ?? holding.current_price;
      if (price === null) {
        continue;
      }

      pricedCount += 1;
      value += price * holding.quantity;
      cost += holding.cost_basis;
      const change = changeSinceLastClose(quote);
      if (change !== null) {
        todayChange += change * holding.quantity;
        hasTodayChange = true;
      }
    }

    const previousValue = value - todayChange;
    return {
      value,
      gain: value - cost,
      gainPercent: cost > 0 ? (value - cost) / cost : null,
      todayChange: hasTodayChange ? todayChange : null,
      todayPercent: hasTodayChange && previousValue > 0 ? todayChange / previousValue : null,
      hasPrices: pricedCount > 0,
    };
  }, [holdings, quotes]);

  const movers = useMemo(() => {
    const ranked = Array.from(new Set([...holdingSymbols, ...watchlistSymbols]))
      .map((symbol) => ({ symbol, ...summarizeQuote(quotes[symbol]) }))
      .map((item) => ({ ...item, move: item.dayChange ?? item.extended?.change ?? null }))
      .filter((item): item is typeof item & { move: number } => item.move !== null)
      .sort((left, right) => right.move - left.move);

    return {
      gainers: ranked.filter((item) => item.move > 0).slice(0, MOVERS_PER_SIDE),
      losers: ranked.filter((item) => item.move < 0).reverse().slice(0, MOVERS_PER_SIDE),
    };
  }, [holdingSymbols, quotes, watchlistSymbols]);

  if (data === null) {
    return (
      <div className="space-y-5">
        <StatTilesSkeleton />
        <div className="grid gap-5 xl:grid-cols-[1.7fr_1fr]">
          <PanelSkeleton height="h-80" />
          <PanelSkeleton height="h-80" />
        </div>
        <PanelSkeleton height="h-48" />
      </div>
    );
  }

  const comparison = data.analytics?.since_purchase ?? null;
  const excessReturn =
    comparison?.portfolio_return != null && comparison.benchmark_return != null
      ? comparison.portfolio_return - comparison.benchmark_return
      : null;
  const benchmark = summarizeQuote(quotes[BENCHMARK]);
  const hasHoldings = holdings.length > 0;
  const quotesLoading = streamSymbols.length > 0 && Object.keys(quotes).length === 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <LiveBadge
          status={status}
          lastUpdated={lastUpdated}
          marketSession={marketSession}
          nextMarketOpen={nextMarketOpen}
          hasExtendedHoursActivity={hasExtendedHoursActivity}
        />
        <MarketStreamErrorToast error={error} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Portfolio value"
          value={!hasHoldings ? "$0.00" : portfolio.hasPrices ? formatCurrency(portfolio.value) : <Skeleton className="h-7 w-32" />}
          detail={
            hasHoldings ? (
              <>
                <span className={cn("font-medium", changeColor(portfolio.gain))}>
                  {portfolio.gain >= 0 ? "+" : ""}
                  {formatCurrency(portfolio.gain)}
                </span>{" "}
                ({formatSignedPercent(portfolio.gainPercent)}) since you bought
              </>
            ) : (
              <Link className="text-primary hover:underline" href="/portfolio">Add your first holding</Link>
            )
          }
        />
        <Stat
          label="Change since last close"
          tone={portfolio.todayChange}
          value={
            !hasHoldings ? "N/A" : quotesLoading ? <Skeleton className="h-7 w-28" /> : portfolio.todayChange === null ? "N/A" : `${portfolio.todayChange >= 0 ? "+" : ""}${formatCurrency(portfolio.todayChange)}`
          }
          detail={hasHoldings ? <><ChangeText value={portfolio.todayPercent} /> on your holdings, at the latest prices</> : "Shows once you have holdings."}
        />
        <Stat
          label="Versus the S&P 500"
          tone={excessReturn}
          value={excessReturn === null ? "N/A" : `${formatSignedPercent(excessReturn)} pts`}
          detail={
            comparison && excessReturn !== null ? (
              <>Your picks {formatSignedPercent(comparison.portfolio_return)} against {formatSignedPercent(comparison.benchmark_return)} for the index since purchase</>
            ) : (
              "Compares your purchases with the S&P 500 over the same dates."
            )
          }
        />
        <Stat
          label="S&P 500 today"
          tone={benchmark.dayChange ?? benchmark.extended?.change ?? null}
          value={
            quotesLoading ? (
              <Skeleton className="h-7 w-24" />
            ) : (
              formatSignedPercent(benchmark.dayChange ?? benchmark.extended?.change ?? null, 2)
            )
          }
          detail={
            benchmark.price !== null ? (
              <>
                SPY at {formatCurrency(benchmark.price)}
                {benchmark.extended ? <> · {benchmark.extended.label.toLowerCase()} <ChangeText value={benchmark.extended.change} /></> : null}
              </>
            ) : (
              "The SPY fund tracks the S&P 500 index."
            )
          }
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.7fr_1fr]">
        <Panel
          title="Portfolio vs S&P 500"
          description="Today's holdings over the past year. Both lines start at 0%."
          action={
            <Button size="sm" variant="ghost" asChild>
              <Link href="/analytics">
                Full analytics
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
          }
        >
          {data.analytics && data.analytics.performance.length > 1 ? (
            <IndexedLineChart
              points={data.analytics.performance}
              series={[
                { key: "portfolio", label: "Your portfolio", color: SERIES_COLORS[0] },
                { key: "benchmark", label: "S&P 500", color: SERIES_COLORS[1] },
              ]}
            />
          ) : (
            <p className="flex h-72 items-center justify-center text-center text-sm text-muted-foreground">
              {hasHoldings ? "Price history for this chart is not available right now." : "Add holdings to compare your portfolio with the market."}
            </p>
          )}
        </Panel>

        <Panel title="Top movers" description="Your holdings and watchlist, by today's change.">
          {quotesLoading ? (
            <RowsSkeleton rows={6} />
          ) : movers.gainers.length + movers.losers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No price changes to show yet.</p>
          ) : (
            <div className="space-y-5">
              {[
                { title: "Up the most", items: movers.gainers, Icon: ArrowUpRight },
                { title: "Down the most", items: movers.losers, Icon: ArrowDownRight },
              ].map(({ title, items, Icon }) =>
                items.length > 0 ? (
                  <div key={title}>
                    <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
                    <ul className="mt-2 divide-y">
                      {items.map((item) => (
                        <li key={item.symbol} className="flex items-center justify-between gap-3 py-2.5">
                          <Link className="min-w-0" href={`/stocks/${item.symbol}`}>
                            <span className="font-semibold text-primary hover:underline">{item.symbol}</span>
                            <span className="ml-2 truncate text-xs text-muted-foreground">{COMPANY_NAMES[item.symbol] ?? ""}</span>
                          </Link>
                          <span className="flex shrink-0 items-center gap-3 text-sm">
                            <span className="text-muted-foreground">{formatCurrency(item.price)}</span>
                            <span className={cn("flex w-20 items-center justify-end gap-1 font-medium", changeColor(item.move))}>
                              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                              {formatSignedPercent(item.move, 2)}
                            </span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null,
              )}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.7fr_1fr]">
        <Panel
          title="Watchlist"
          description="Latest price, today's change and the past month."
          action={
            <Button size="sm" variant="outline" asChild>
              <Link href="/watchlists">Manage</Link>
            </Button>
          }
        >
          {watchlistSymbols.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Your watchlists are empty. <Link className="text-primary hover:underline" href="/watchlists">Add stocks to follow</Link>.
            </p>
          ) : (
            <div className="-mx-5 overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="border-b text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    <th className="px-5 pb-2 font-medium">Stock</th>
                    <th className="px-3 pb-2 text-right font-medium">Price</th>
                    <th className="px-3 pb-2 text-right font-medium">Today</th>
                    <th className="px-5 pb-2 text-right font-medium">Past month</th>
                  </tr>
                </thead>
                <tbody>
                  {watchlistSymbols.map((symbol) => {
                    const summary = summarizeQuote(quotes[symbol]);
                    const closes = monthlyCloses[symbol];
                    const monthChange = closes && closes.length > 1 ? closes[closes.length - 1] / closes[0] - 1 : null;

                    return (
                      <tr key={symbol} className="border-b last:border-b-0">
                        <td className="px-5 py-3">
                          <Link className="font-semibold text-primary hover:underline" href={`/stocks/${symbol}`}>
                            {symbol}
                          </Link>
                          <p className="text-xs text-muted-foreground">{COMPANY_NAMES[symbol] ?? ""}</p>
                        </td>
                        <td className="px-3 py-3 text-right">
                          {summary.price === null ? <Skeleton className="ml-auto h-4 w-16" /> : formatCurrency(summary.price)}
                          {summary.extended ? (
                            <p className="text-xs text-muted-foreground">
                              {summary.extended.label} <ChangeText value={summary.extended.change} />
                            </p>
                          ) : null}
                        </td>
                        <td className="px-3 py-3 text-right">
                          {summary.dayChange === null ? <span className="text-muted-foreground">N/A</span> : <ChangeText value={summary.dayChange} />}
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex items-center justify-end gap-3">
                            {closes === undefined ? (
                              <Skeleton className="h-7 w-24" />
                            ) : (
                              <Sparkline values={closes} color={SERIES_COLORS[0]} label={`${symbol} over the past month`} />
                            )}
                            <span className="w-16 text-right text-xs">
                              {monthChange === null ? "" : <ChangeText value={monthChange} />}
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        {aside}
      </div>
    </div>
  );
}
