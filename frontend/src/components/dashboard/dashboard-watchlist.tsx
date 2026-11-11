"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { LivePrice } from "@/components/market/live-price";
import { MarketStreamErrorToast } from "@/components/market/market-stream-error-toast";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast-provider";
import { getWatchlists, type Watchlist } from "@/lib/api";
import { useMarketStream, type LiveQuote } from "@/lib/market-stream";
import { cn } from "@/lib/utils";

const MAX_DASHBOARD_SYMBOLS = 5;

const COMPANY_NAMES: Record<string, string> = {
  AAPL: "Apple",
  AMZN: "Amazon",
  GOOGL: "Alphabet",
  JPM: "JPMorgan Chase",
  META: "Meta Platforms",
  MSFT: "Microsoft",
  NVDA: "NVIDIA",
  TSLA: "Tesla",
};

function getUniqueWatchlistSymbols(watchlists: Watchlist[]) {
  return Array.from(
    new Set(
      watchlists.flatMap((watchlist) =>
        watchlist.stocks.map((stock) => stock.ticker.trim().toUpperCase()).filter(Boolean),
      ),
    ),
  ).slice(0, MAX_DASHBOARD_SYMBOLS);
}

function formatChange(quote: LiveQuote | undefined) {
  const changePercent = quote?.changePercent;

  if (changePercent === null || changePercent === undefined) {
    return null;
  }

  return `${changePercent >= 0 ? "+" : ""}${changePercent.toFixed(2)}%`;
}

function formatVolume(value: number | null | undefined) {
  if (!value) {
    return "Waiting";
  }

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function DashboardWatchlist() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { showToast } = useToast();
  const { quotes, error } = useMarketStream(symbols);
  const hasSymbols = symbols.length > 0;

  useEffect(() => {
    let isMounted = true;

    async function loadWatchlistSymbols() {
      setIsLoading(true);

      try {
        const watchlists = await getWatchlists();
        const nextSymbols = getUniqueWatchlistSymbols(watchlists);

        if (isMounted) {
          setSymbols(nextSymbols);
        }
      } catch (caughtError) {
        if (isMounted) {
          showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to load dashboard watchlist" });
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadWatchlistSymbols();

    return () => {
      isMounted = false;
    };
  }, [showToast]);

  const rows = useMemo(
    () =>
      symbols.map((symbol) => {
        const quote = quotes[symbol];

        return {
          symbol,
          company: COMPANY_NAMES[symbol] ?? symbol,
          quote,
          volume: formatVolume(quote?.todayVolume),
          change: formatChange(quote),
          isUp: (quote?.changePercent ?? 0) >= 0,
        };
      }),
    [quotes, symbols],
  );

  if (isLoading) {
    return <p className="rounded-md border bg-background/40 p-4 text-sm text-muted-foreground">Loading watchlist prices...</p>;
  }

  if (!hasSymbols) {
    return (
      <div className="rounded-md border bg-background/40 p-5">
        <p className="text-sm font-medium">No watchlist symbols yet</p>
        <p className="mt-2 text-sm text-muted-foreground">Add stocks to your watchlist to see live dashboard prices here.</p>
        <Button className="mt-4" size="sm" variant="secondary" asChild>
          <Link href="/watchlists">Manage Lists</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-md border">
        <div className="min-w-[760px]">
          <div className="grid grid-cols-[0.7fr_1.1fr_1.35fr_0.8fr_0.8fr] bg-secondary px-4 py-3 text-xs font-medium uppercase text-muted-foreground">
            <span>Symbol</span>
            <span>Company</span>
            <span>Price</span>
            <span>Volume</span>
            <span className="text-right">Today</span>
          </div>
          {rows.map((stock) => (
            <div
              key={stock.symbol}
              className="grid grid-cols-[0.7fr_1.1fr_1.35fr_0.8fr_0.8fr] items-center border-t px-4 py-4 text-sm"
            >
              <Link className="font-semibold text-primary hover:underline" href={`/stocks/${stock.symbol}`}>
                {stock.symbol}
              </Link>
              <span className="text-muted-foreground">{stock.company}</span>
              <LivePrice quote={stock.quote} compact />
              <span className="text-muted-foreground">{stock.volume}</span>
              <span
                className={cn(
                  "text-right font-medium",
                  stock.change === null ? "text-muted-foreground" : stock.isUp ? "text-emerald-400" : "text-red-400",
                )}
              >
                {stock.change ?? "Waiting"}
              </span>
            </div>
          ))}
        </div>
      </div>
      <MarketStreamErrorToast error={error} />
    </div>
  );
}
