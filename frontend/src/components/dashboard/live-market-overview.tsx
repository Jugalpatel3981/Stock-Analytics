"use client";

import { RotateCcw, Save, Star } from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { LiveBadge } from "@/components/market/live-badge";
import { MarketStreamErrorToast } from "@/components/market/market-stream-error-toast";
import { LivePrice } from "@/components/market/live-price";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast-provider";
import { getWatchlists } from "@/lib/api";
import { useMarketStream } from "@/lib/market-stream";

type MarketSymbol = {
  symbol: string;
  label: string;
};

const DEFAULT_MARKET_SYMBOLS: MarketSymbol[] = [
  { symbol: "SPY", label: "S&P 500 ETF" },
  { symbol: "QQQ", label: "Nasdaq 100 ETF" },
  { symbol: "DIA", label: "Dow ETF" },
  { symbol: "NVDA", label: "NVIDIA" },
];

const STORAGE_KEY = "dashboard-market-symbols";
const MAX_SYMBOLS = 4;

function normalizeSymbols(value: string) {
  return Array.from(
    new Set(
      value
        .split(",")
        .map((symbol) => symbol.trim().toUpperCase())
        .filter((symbol) => /^[A-Z.]{1,8}$/.test(symbol)),
    ),
  ).slice(0, MAX_SYMBOLS);
}

function toMarketSymbols(symbols: string[], label: string): MarketSymbol[] {
  return symbols.map((symbol) => ({ symbol, label }));
}

export function LiveMarketOverview() {
  const [marketSymbols, setMarketSymbols] = useState<MarketSymbol[]>(DEFAULT_MARKET_SYMBOLS);
  const [watchlistSymbols, setWatchlistSymbols] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState(DEFAULT_MARKET_SYMBOLS.map((item) => item.symbol).join(", "));
  const [sourceLabel, setSourceLabel] = useState("Default set");
  const { showToast } = useToast();
  const symbols = useMemo(() => marketSymbols.map((item) => item.symbol), [marketSymbols]);
  const { quotes, status, error, lastUpdated, marketSession, nextMarketOpen, hasExtendedHoursActivity } = useMarketStream(symbols);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboardSymbols() {

      try {
        const savedSymbols = normalizeSymbols(localStorage.getItem(STORAGE_KEY) ?? "");
        const watchlists = await getWatchlists();
        const symbolsFromWatchlists = Array.from(
          new Set(watchlists.flatMap((watchlist) => watchlist.stocks.map((stock) => stock.ticker.toUpperCase()))),
        ).slice(0, MAX_SYMBOLS);

        if (!isMounted) {
          return;
        }

        setWatchlistSymbols(symbolsFromWatchlists);
        if (savedSymbols.length > 0) {
          setMarketSymbols(toMarketSymbols(savedSymbols, "Custom dashboard symbol"));
          setInputValue(savedSymbols.join(", "));
          setSourceLabel("Custom set");
        } else if (symbolsFromWatchlists.length > 0) {
          setMarketSymbols(toMarketSymbols(symbolsFromWatchlists, "From your watchlist"));
          setInputValue(symbolsFromWatchlists.join(", "));
          setSourceLabel("Watchlist set");
        }
      } catch (caughtError) {
        if (isMounted) {
          showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to load watchlist symbols" });
        }
      }
    }

    loadDashboardSymbols();

    return () => {
      isMounted = false;
    };
  }, [showToast]);

  function handleSaveSymbols(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextSymbols = normalizeSymbols(inputValue);

    if (nextSymbols.length === 0) {
      showToast({ message: "Enter at least one valid ticker symbol." });
      return;
    }

    localStorage.setItem(STORAGE_KEY, nextSymbols.join(","));
    setMarketSymbols(toMarketSymbols(nextSymbols, "Custom dashboard symbol"));
    setInputValue(nextSymbols.join(", "));
    setSourceLabel("Custom set");
  }

  function handleUseWatchlist() {
    if (watchlistSymbols.length === 0) {
      showToast({ message: "Add stocks to a watchlist first, then return to the dashboard." });
      return;
    }

    localStorage.removeItem(STORAGE_KEY);
    setMarketSymbols(toMarketSymbols(watchlistSymbols, "From your watchlist"));
    setInputValue(watchlistSymbols.join(", "));
    setSourceLabel("Watchlist set");
  }

  function handleResetSymbols() {
    localStorage.removeItem(STORAGE_KEY);
    setMarketSymbols(DEFAULT_MARKET_SYMBOLS);
    setInputValue(DEFAULT_MARKET_SYMBOLS.map((item) => item.symbol).join(", "));
    setSourceLabel("Default set");
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <LiveBadge
            status={status}
            lastUpdated={lastUpdated}
            marketSession={marketSession}
            nextMarketOpen={nextMarketOpen}
            hasExtendedHoursActivity={hasExtendedHoursActivity}
          />
          <p className="mt-2 text-xs text-muted-foreground">{sourceLabel}</p>
        </div>
        <form className="flex flex-col gap-2 sm:flex-row sm:items-center" onSubmit={handleSaveSymbols}>
          <Input
            aria-label="Dashboard market symbols"
            className="h-9 min-w-0 uppercase sm:w-72"
            maxLength={48}
            onChange={(event) => setInputValue(event.target.value)}
            placeholder="AAPL, TSLA, NVDA, MSFT"
            value={inputValue}
          />
          <div className="flex gap-2">
            <Button type="submit" size="sm">
              <Save className="h-4 w-4" aria-hidden="true" />
              Save
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={handleUseWatchlist}>
              <Star className="h-4 w-4" aria-hidden="true" />
              Watchlist
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={handleResetSymbols} aria-label="Reset market symbols">
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </form>
      </div>
      <MarketStreamErrorToast error={error} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {marketSymbols.map((item) => (
          <div key={item.symbol} className="rounded-md border bg-background/40 p-4">
            <div className="mb-3">
              <p className="text-sm font-semibold">{item.symbol}</p>
              <p className="text-xs text-muted-foreground">{item.label}</p>
            </div>
            <LivePrice quote={quotes[item.symbol]} compact />
          </div>
        ))}
      </div>
    </div>
  );
}


