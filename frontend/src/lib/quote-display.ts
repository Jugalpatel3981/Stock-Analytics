import type { LiveQuote } from "@/lib/market-stream";

export type QuoteSummary = {
  /** The latest price, including pre-market or after-hours trading. */
  price: number | null;
  /** The regular session's move against the previous close, as a fraction. */
  dayChange: number | null;
  /** The move outside regular hours against the regular session price. */
  extended: { label: "Pre-market" | "After hours"; change: number } | null;
};

function fractionChange(current: number | null | undefined, base: number | null | undefined) {
  if (current == null || base == null || base === 0) {
    return null;
  }

  return current / base - 1;
}

/**
 * Splits a quote into the regular session's move and any move outside regular hours, so
 * tables show both clearly instead of mixing them into one number.
 */
export function summarizeQuote(quote: LiveQuote | undefined): QuoteSummary {
  if (!quote) {
    return { price: null, dayChange: null, extended: null };
  }

  const extendedPrice = quote.hasExtendedHoursActivity ? (quote.extendedHoursPrice ?? quote.price) : null;

  if (quote.marketSession === "PRE_MARKET") {
    const base = quote.regularPrice ?? quote.previousClose;
    const change = fractionChange(extendedPrice, base);
    return {
      price: extendedPrice ?? base ?? quote.price,
      dayChange: null,
      extended: change === null ? null : { label: "Pre-market", change },
    };
  }

  if (quote.marketSession === "AFTER_HOURS") {
    const close = quote.regularPrice ?? quote.price;
    const change = fractionChange(extendedPrice, close);
    return {
      price: extendedPrice ?? close,
      dayChange: fractionChange(close, quote.previousClose),
      extended: change === null ? null : { label: "After hours", change },
    };
  }

  return {
    price: quote.price,
    dayChange: quote.changePercent !== null ? quote.changePercent / 100 : fractionChange(quote.price, quote.previousClose),
    extended: null,
  };
}

/** Change from the last regular close to the latest price, including extended hours. */
export function changeSinceLastClose(quote: LiveQuote | undefined) {
  const summary = summarizeQuote(quote);
  if (!quote || summary.price === null) {
    return null;
  }

  const base = quote.marketSession === "PRE_MARKET" ? (quote.regularPrice ?? quote.previousClose) : quote.previousClose;
  return base ? summary.price - base : null;
}
