"use client";

import Link from "next/link";

import { LiveBadge } from "@/components/market/live-badge";
import { MarketStreamErrorToast } from "@/components/market/market-stream-error-toast";
import { LivePrice } from "@/components/market/live-price";
import { useMarketStream } from "@/lib/market-stream";

const popularStocks = [
  { symbol: "AAPL", company: "Apple" },
  { symbol: "MSFT", company: "Microsoft" },
  { symbol: "NVDA", company: "NVIDIA" },
  { symbol: "AMZN", company: "Amazon" },
  { symbol: "GOOGL", company: "Alphabet" },
  { symbol: "META", company: "Meta Platforms" },
  { symbol: "TSLA", company: "Tesla" },
  { symbol: "JPM", company: "JPMorgan Chase" },
];

export function PopularLiveStocks() {
  const symbols = popularStocks.map((stock) => stock.symbol);
  const { quotes, status, error, lastUpdated, marketSession, nextMarketOpen, hasExtendedHoursActivity } = useMarketStream(symbols);

  return (
    <div className="space-y-3">
      <LiveBadge
        status={status}
        lastUpdated={lastUpdated}
        marketSession={marketSession}
        nextMarketOpen={nextMarketOpen}
        hasExtendedHoursActivity={hasExtendedHoursActivity}
      />
      <MarketStreamErrorToast error={error} />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {popularStocks.map((stock) => (
          <div key={stock.symbol} className="rounded-md border bg-background/40 p-4">
            <div className="mb-4">
              <Link className="text-lg font-semibold text-primary hover:underline" href={`/stocks/${stock.symbol}`}>
                {stock.symbol}
              </Link>
              <p className="mt-1 text-xs text-muted-foreground">{stock.company}</p>
            </div>
            <LivePrice quote={quotes[stock.symbol]} />
          </div>
        ))}
      </div>
    </div>
  );
}

