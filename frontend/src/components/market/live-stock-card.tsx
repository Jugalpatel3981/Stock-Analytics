"use client";

import Link from "next/link";

import { LiveBadge } from "@/components/market/live-badge";
import { MarketStreamErrorToast } from "@/components/market/market-stream-error-toast";
import { LivePrice } from "@/components/market/live-price";
import { useMarketStream } from "@/lib/market-stream";

type LiveStockCardProps = {
  symbol: string;
  company?: string | null;
  initialPrice?: number | null;
  initialVolume?: number | null;
  currency?: string | null;
};

export function LiveStockCard({
  symbol,
  company,
  initialPrice = null,
  initialVolume = null,
  currency = "USD",
}: LiveStockCardProps) {
  const { quotes, status, error, lastUpdated, marketSession, nextMarketOpen, hasExtendedHoursActivity } = useMarketStream(
    [symbol],
    { initialPrices: { [symbol.toUpperCase()]: initialPrice } },
  );
  const normalizedSymbol = symbol.toUpperCase();

  return (
    <div className="rounded-md border bg-background/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Link className="text-lg font-semibold text-primary hover:underline" href={`/stocks/${normalizedSymbol}`}>
            {normalizedSymbol}
          </Link>
          <p className="mt-1 text-xs text-muted-foreground">{company ?? "Live market data"}</p>
        </div>
        <LiveBadge
          status={status}
          lastUpdated={lastUpdated}
          marketSession={marketSession}
          nextMarketOpen={nextMarketOpen}
          hasExtendedHoursActivity={hasExtendedHoursActivity}
        />
      </div>
      <div className="mt-4">
        <LivePrice
          quote={quotes[normalizedSymbol]}
          fallbackPrice={initialPrice}
          fallbackVolume={initialVolume}
          currency={currency}
        />
      </div>
      <MarketStreamErrorToast error={error} />
    </div>
  );
}

