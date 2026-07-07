"use client";

import { useEffect, useMemo, useState } from "react";

import { getMarketQuotes, type MarketSession } from "@/lib/api";
import { getMarketStreamUrl } from "@/lib/env";

export type LiveQuote = {
  symbol: string;
  price: number;
  timestamp: string;
  previousPrice: number | null;
  previousClose: number | null;
  regularPrice: number | null;
  extendedHoursPrice: number | null;
  hasExtendedHoursActivity: boolean;
  extendedHoursStatus: "ACTIVE" | "WAITING" | "NONE";
  extendedHoursSource: string | null;
  marketSession: MarketSession;
  nextMarketOpen: string | null;
  change: number | null;
  changePercent: number | null;
  todayVolume: number | null;
  dayHigh: number | null;
  dayLow: number | null;
  openPrice: number | null;
};

export type StreamStatus = "idle" | "connecting" | "connected" | "error";

type UseMarketStreamOptions = {
  initialPrices?: Record<string, number | null>;
  snapshotIntervalMs?: number;
};

const DEFAULT_SNAPSHOT_INTERVAL_MS = 30000;
const liveQuoteMemory: Record<string, LiveQuote> = {};

function timestampValue(value: string | null | undefined) {
  if (!value) {
    return 0;
  }

  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function rememberQuote(quote: LiveQuote) {
  liveQuoteMemory[quote.symbol] = quote;
}

function mergeSnapshotQuote(
  previous: LiveQuote | undefined,
  snapshot: Awaited<ReturnType<typeof getMarketQuotes>>[number],
  snapshotTimestamp: string,
): LiveQuote {
  const symbol = snapshot.symbol.toUpperCase();
  const snapshotTime = timestampValue(snapshot.timestamp ?? snapshotTimestamp);
  const previousTime = timestampValue(previous?.timestamp);
  const isExtendedSession = snapshot.market_session === "PRE_MARKET" || snapshot.market_session === "AFTER_HOURS";
  const shouldKeepNewerExtendedTrade =
    Boolean(previous?.hasExtendedHoursActivity) &&
    isExtendedSession &&
    !snapshot.has_extended_hours_activity &&
    previousTime > snapshotTime;

  return {
    symbol,
    price: shouldKeepNewerExtendedTrade ? previous?.price ?? snapshot.current_price : snapshot.current_price,
    timestamp: shouldKeepNewerExtendedTrade ? previous?.timestamp ?? snapshotTimestamp : snapshot.timestamp ?? snapshotTimestamp,
    previousPrice: previous?.price ?? null,
    previousClose: snapshot.previous_close,
    regularPrice: snapshot.regular_price,
    extendedHoursPrice: shouldKeepNewerExtendedTrade
      ? previous?.extendedHoursPrice ?? previous?.price ?? snapshot.extended_hours_price
      : snapshot.extended_hours_price,
    hasExtendedHoursActivity: shouldKeepNewerExtendedTrade ? true : snapshot.has_extended_hours_activity,
    extendedHoursStatus: shouldKeepNewerExtendedTrade ? "ACTIVE" : snapshot.extended_hours_status,
    extendedHoursSource: shouldKeepNewerExtendedTrade
      ? previous?.extendedHoursSource ?? "Finnhub"
      : snapshot.extended_hours_source,
    marketSession: snapshot.market_session,
    nextMarketOpen: snapshot.next_market_open,
    change: shouldKeepNewerExtendedTrade ? previous?.change ?? snapshot.change : snapshot.change,
    changePercent: shouldKeepNewerExtendedTrade ? previous?.changePercent ?? snapshot.change_percent : snapshot.change_percent,
    todayVolume: snapshot.volume,
    dayHigh: snapshot.high,
    dayLow: snapshot.low,
    openPrice: snapshot.open,
  };
}

export function useMarketStream(symbols: string[], options: UseMarketStreamOptions = {}) {
  const [quotes, setQuotes] = useState<Record<string, LiveQuote>>({});
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [marketSession, setMarketSession] = useState<MarketSession>("CLOSED");
  const [nextMarketOpen, setNextMarketOpen] = useState<string | null>(null);

  const symbolKey = useMemo(
    () => Array.from(new Set(symbols.map((symbol) => symbol.trim().toUpperCase()).filter(Boolean))).sort().join(","),
    [symbols],
  );
  const initialPricesKey = JSON.stringify(options.initialPrices ?? {});
  const hasExtendedHoursActivity = useMemo(
    () =>
      Object.values(quotes).some(
        (quote) =>
          quote.hasExtendedHoursActivity &&
          (quote.marketSession === "PRE_MARKET" || quote.marketSession === "AFTER_HOURS"),
      ),
    [quotes],
  );

  useEffect(() => {
    if (!symbolKey) {
      setStatus("idle");
      return;
    }

    const url = new URL(getMarketStreamUrl());
    url.searchParams.set("symbols", symbolKey);

    const socket = new WebSocket(url.toString());
    const initialPrices = JSON.parse(initialPricesKey) as Record<string, number | null>;
    const requestedSymbols = symbolKey.split(",");

    setStatus("connecting");
    setError(null);

    const rememberedQuotes = requestedSymbols.reduce<Record<string, LiveQuote>>((nextQuotes, symbol) => {
      const remembered = liveQuoteMemory[symbol];
      if (remembered) {
        nextQuotes[symbol] = remembered;
      }

      return nextQuotes;
    }, {});

    if (Object.keys(rememberedQuotes).length > 0) {
      const newestRememberedQuote = Object.values(rememberedQuotes).sort(
        (firstQuote, secondQuote) => timestampValue(secondQuote.timestamp) - timestampValue(firstQuote.timestamp),
      )[0];

      setQuotes((currentQuotes) => ({ ...rememberedQuotes, ...currentQuotes }));
      setLastUpdated(newestRememberedQuote.timestamp);
      setMarketSession(newestRememberedQuote.marketSession);
      setNextMarketOpen(newestRememberedQuote.nextMarketOpen);
    }

    socket.onopen = () => {
      setStatus("connected");
    };

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as {
        type: string;
        symbol?: string;
        price?: number;
        timestamp?: string;
        message?: string;
      };

      if (payload.type === "error") {
        setStatus("error");
        setError(payload.message ?? "Live stream unavailable");
        return;
      }

      if (payload.type !== "trade" || !payload.symbol || typeof payload.price !== "number") {
        return;
      }

      const symbol = payload.symbol.toUpperCase();
      const price = payload.price;
      const timestamp = payload.timestamp ?? new Date().toISOString();

      setQuotes((currentQuotes) => {
        const previous = currentQuotes[symbol] ?? liveQuoteMemory[symbol];
        const initialPrice = initialPrices[symbol] ?? previous?.price ?? null;
        const previousPrice = previous?.price ?? null;
        const previousClose = previous?.previousClose ?? null;
        const regularPrice = previous?.regularPrice ?? null;
        const extendedHoursPrice = previous?.extendedHoursPrice ?? null;
        const extendedHoursSource = previous?.extendedHoursSource ?? null;
        const hasTradeExtendedHoursActivity =
          previous?.marketSession === "PRE_MARKET" || previous?.marketSession === "AFTER_HOURS";
        const hasExtendedActivity = previous?.hasExtendedHoursActivity || hasTradeExtendedHoursActivity;
        const quoteMarketSession = previous?.marketSession ?? "CLOSED";
        const quoteNextMarketOpen = previous?.nextMarketOpen ?? null;
        const changeBase = previousClose ?? initialPrice ?? previousPrice;
        const change = changeBase !== null ? price - changeBase : null;
        const changePercent = changeBase ? ((change ?? 0) / changeBase) * 100 : null;
        const nextQuote: LiveQuote = {
          symbol,
          price,
          timestamp,
          previousPrice,
          previousClose,
          regularPrice,
          extendedHoursPrice: hasExtendedActivity ? price : extendedHoursPrice,
          hasExtendedHoursActivity: hasExtendedActivity,
          extendedHoursStatus: hasExtendedActivity ? "ACTIVE" : previous?.extendedHoursStatus ?? "NONE",
          extendedHoursSource: hasTradeExtendedHoursActivity ? "Finnhub" : extendedHoursSource,
          marketSession: quoteMarketSession,
          nextMarketOpen: quoteNextMarketOpen,
          change,
          changePercent,
          todayVolume: previous?.todayVolume ?? null,
          dayHigh: previous?.dayHigh ?? null,
          dayLow: previous?.dayLow ?? null,
          openPrice: previous?.openPrice ?? null,
        };

        rememberQuote(nextQuote);

        return {
          ...currentQuotes,
          [symbol]: nextQuote,
        };
      });
      setLastUpdated(timestamp);
    };

    socket.onerror = () => {
      setStatus("error");
      setError("Live stream connection failed");
    };

    socket.onclose = () => {
      setStatus((currentStatus) => (currentStatus === "error" ? currentStatus : "idle"));
    };

    return () => {
      socket.close();
    };
  }, [initialPricesKey, symbolKey]);

  useEffect(() => {
    if (!symbolKey) {
      return;
    }

    const requestedSymbols = symbolKey.split(",");
    const snapshotIntervalMs = options.snapshotIntervalMs ?? DEFAULT_SNAPSHOT_INTERVAL_MS;
    let isActive = true;

    async function refreshSnapshots() {
      try {
        const snapshots = await getMarketQuotes(requestedSymbols);
        if (!isActive) {
          return;
        }

        const snapshotTimestamp = new Date().toISOString();
        setQuotes((currentQuotes) => {
          const nextQuotes = { ...currentQuotes };

          for (const snapshot of snapshots) {
            const symbol = snapshot.symbol.toUpperCase();
            const previous = currentQuotes[symbol] ?? liveQuoteMemory[symbol];
            const nextQuote = mergeSnapshotQuote(previous, snapshot, snapshotTimestamp);
            nextQuotes[symbol] = nextQuote;
            rememberQuote(nextQuote);
          }

          return nextQuotes;
        });

        if (snapshots.length > 0) {
          const firstSnapshot = snapshots[0];
          const updatedAt = snapshotTimestamp;
          setLastUpdated(updatedAt);
          setMarketSession(firstSnapshot.market_session);
          setNextMarketOpen(firstSnapshot.next_market_open);
        }
      } catch (caughtError) {
        if (!isActive) {
          return;
        }

        setError(caughtError instanceof Error ? caughtError.message : "Unable to load Finnhub quote snapshot");
      }
    }

    refreshSnapshots();
    const snapshotIntervalId = window.setInterval(refreshSnapshots, snapshotIntervalMs);

    return () => {
      isActive = false;
      window.clearInterval(snapshotIntervalId);
    };
  }, [options.snapshotIntervalMs, symbolKey]);

  return { quotes, status, error, lastUpdated, marketSession, nextMarketOpen, hasExtendedHoursActivity };
}
