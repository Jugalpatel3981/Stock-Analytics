import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import type { LiveQuote } from "@/lib/market-stream";
import { cn } from "@/lib/utils";

type LivePriceProps = {
  quote?: LiveQuote;
  fallbackPrice?: number | null;
  fallbackVolume?: number | null;
  currency?: string | null;
  compact?: boolean;
};

function formatCurrency(value: number | null | undefined, currency: string | null | undefined) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency ?? "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function sessionPriceLabel(quote: LiveQuote | undefined, currency: string | null | undefined) {
  if (!quote) {
    return "Change pending";
  }

  if (quote.marketSession === "PRE_MARKET") {
    if (!quote.hasExtendedHoursActivity) {
      return "Waiting for pre-market trade";
    }

    return `Pre-market ${formatCurrency(quote.extendedHoursPrice ?? quote.price, currency)}`;
  }

  if (quote.marketSession === "AFTER_HOURS") {
    if (!quote.hasExtendedHoursActivity) {
      return "Waiting for after-hours trade";
    }

    return `After Hours Price ${formatCurrency(quote.extendedHoursPrice ?? quote.price, currency)}`;
  }

  if (quote.marketSession === "CLOSED") {
    return `Last close ${formatCurrency(quote.regularPrice ?? quote.price, currency)}`;
  }

  return quote.change === null ? "Change pending" : null;
}

function referencePriceLabel(quote: LiveQuote | undefined, currency: string | null | undefined) {
  if (!quote) {
    return null;
  }

  if (quote.marketSession === "PRE_MARKET") {
    return `Prev close ${formatCurrency(quote.regularPrice ?? quote.previousClose, currency)}`;
  }

  if (quote.marketSession === "AFTER_HOURS") {
    const source = quote.extendedHoursSource ? ` - ${quote.extendedHoursSource}` : "";
    return `Regular close ${formatCurrency(quote.regularPrice ?? quote.previousClose, currency)}${source}`;
  }

  if (quote.marketSession === "CLOSED" && quote.nextMarketOpen) {
    return `Next open ${new Date(quote.nextMarketOpen).toLocaleString("en-US", {
      weekday: "short",
      hour: "numeric",
      minute: "2-digit",
    })}`;
  }

  return null;
}

function displayPrice(quote: LiveQuote | undefined, fallbackPrice: number | null, currency: string | null | undefined) {
  if (!quote) {
    return formatCurrency(fallbackPrice, currency);
  }

  if (quote.marketSession === "AFTER_HOURS" && !quote.hasExtendedHoursActivity) {
    return formatCurrency(quote.regularPrice ?? quote.previousClose ?? quote.price, currency);
  }

  if (quote.marketSession === "PRE_MARKET" && !quote.hasExtendedHoursActivity) {
    return formatCurrency(quote.regularPrice ?? quote.previousClose ?? fallbackPrice, currency);
  }

  return formatCurrency(quote.extendedHoursPrice ?? quote.price, currency);
}

export function LivePrice({
  quote,
  fallbackPrice = null,
  fallbackVolume = null,
  currency = "USD",
  compact = false,
}: LivePriceProps) {
  const change = quote?.change ?? null;
  const changePercent = quote?.changePercent ?? null;
  const isUp = (change ?? 0) > 0;
  const isDown = (change ?? 0) < 0;
  const Icon = isUp ? ArrowUpRight : isDown ? ArrowDownRight : Minus;
  const sessionLabel = sessionPriceLabel(quote, currency);
  const referenceLabel = referencePriceLabel(quote, currency);
  const isWaitingForExtendedTrade =
    Boolean(quote) &&
    quote?.extendedHoursStatus === "WAITING" &&
    (quote.marketSession === "PRE_MARKET" || quote.marketSession === "AFTER_HOURS");
  const showChangePercent = !isWaitingForExtendedTrade;
  const volume = quote?.todayVolume ?? fallbackVolume;

  return (
    <div className={compact ? "space-y-1" : "space-y-2"}>
      <div className="flex items-center gap-2">
        <p className={compact ? "text-base font-semibold" : "text-2xl font-semibold tracking-normal"}>
          {displayPrice(quote, fallbackPrice, currency)}
        </p>
        <Icon
          className={cn(
            "h-4 w-4",
            isUp && "text-emerald-400",
            isDown && "text-red-400",
            !isUp && !isDown && "text-muted-foreground",
          )}
          aria-hidden="true"
        />
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          className={cn(
            isUp && !isWaitingForExtendedTrade && "text-emerald-400",
            isDown && !isWaitingForExtendedTrade && "text-red-400",
            (!isUp || isWaitingForExtendedTrade) && (!isDown || isWaitingForExtendedTrade) && "text-muted-foreground",
          )}
        >
          {sessionLabel ?? `${isUp ? "+" : ""}${formatCurrency(change, currency)}`}
          {showChangePercent && changePercent !== null ? ` (${isUp ? "+" : ""}${changePercent.toFixed(2)}%)` : ""}
        </span>
        {referenceLabel ? <span className="text-muted-foreground">{referenceLabel}</span> : null}
        <span className="text-muted-foreground">Vol {formatNumber(volume)}</span>
      </div>
    </div>
  );
}
