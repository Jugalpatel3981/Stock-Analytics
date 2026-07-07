"use client";

import { Activity, BadgeDollarSign, BarChart3, BriefcaseBusiness } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { MetricCard } from "@/components/dashboard/metric-card";
import { useToast } from "@/components/ui/toast-provider";
import { getPortfolioSummary, getWatchlists, type PortfolioSummary } from "@/lib/api";
import { useMarketStream } from "@/lib/market-stream";

const MARKET_OVERVIEW_SYMBOLS = ["SPY", "QQQ", "DIA"];

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatSignedCurrency(value: number) {
  const formattedValue = formatCurrency(Math.abs(value));
  return `${value >= 0 ? "+" : "-"}${formattedValue}`;
}

function formatSignedPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function getMarketOverview(spyChange: number | null, qqqChange: number | null, diaChange: number | null) {
  const availableChanges = [spyChange, qqqChange, diaChange].filter((value): value is number => value !== null);

  if (availableChanges.length === 0) {
    return {
      value: "Waiting",
      change: "Live market data pending",
      trend: "neutral" as const,
    };
  }

  const averageChange = availableChanges.reduce((total, value) => total + value, 0) / availableChanges.length;
  const technologyLeading = qqqChange !== null && spyChange !== null && qqqChange > spyChange;

  if (averageChange > 0.25) {
    return {
      value: "Risk-On",
      change: technologyLeading ? "Technology leading" : `${formatSignedPercent(averageChange)} index average`,
      trend: "up" as const,
    };
  }

  if (averageChange < -0.25) {
    return {
      value: "Risk-Off",
      change: `${formatSignedPercent(averageChange)} index average`,
      trend: "down" as const,
    };
  }

  return {
    value: "Mixed",
    change: `${formatSignedPercent(averageChange)} index average`,
    trend: "neutral" as const,
  };
}

export function DashboardMetrics() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [watchlistCount, setWatchlistCount] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    let isMounted = true;

    async function loadMetrics() {
      setIsLoading(true);

      try {
        const [portfolioSummary, watchlists] = await Promise.all([
          getPortfolioSummary(),
          getWatchlists(),
        ]);
        const uniqueWatchlistSymbols = new Set(
          watchlists.flatMap((watchlist) => watchlist.stocks.map((stock) => stock.ticker.toUpperCase())),
        );

        if (isMounted) {
          setPortfolio(portfolioSummary);
          setWatchlistCount(uniqueWatchlistSymbols.size);
        }
      } catch (caughtError) {
        if (isMounted) {
          showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to load dashboard metrics" });
          setPortfolio(null);
          setWatchlistCount(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadMetrics();

    return () => {
      isMounted = false;
    };
  }, [showToast]);

  const portfolioSymbols = useMemo(
    () => Array.from(new Set(portfolio?.holdings.map((holding) => holding.symbol.toUpperCase()) ?? [])),
    [portfolio],
  );
  const streamSymbols = useMemo(
    () => Array.from(new Set([...portfolioSymbols, ...MARKET_OVERVIEW_SYMBOLS])),
    [portfolioSymbols],
  );
  const { quotes } = useMarketStream(streamSymbols);

  const livePortfolio = useMemo(() => {
    if (!portfolio) {
      return {
        totalValue: 0,
        todayGain: 0,
        todayGainPercent: 0,
      };
    }

    let totalValue = 0;
    let todayGain = 0;

    for (const holding of portfolio.holdings) {
      const quote = quotes[holding.symbol];
      const livePrice = quote?.price ?? holding.current_price ?? 0;
      totalValue += livePrice * holding.quantity;

      if (quote?.change !== null && quote?.change !== undefined) {
        todayGain += quote.change * holding.quantity;
      }
    }

    const previousValue = totalValue - todayGain;
    const todayGainPercent = previousValue > 0 ? (todayGain / previousValue) * 100 : 0;

    return { totalValue, todayGain, todayGainPercent };
  }, [portfolio, quotes]);

  const marketOverview = getMarketOverview(
    quotes.SPY?.changePercent ?? null,
    quotes.QQQ?.changePercent ?? null,
    quotes.DIA?.changePercent ?? null,
  );

  const metrics = [
    {
      title: "Portfolio Value",
      value: isLoading ? "Loading..." : formatCurrency(livePortfolio.totalValue),
      change: portfolio?.holdings.length ? `${formatSignedCurrency(portfolio.total_gain_loss)} total return` : "Add holdings to track value",
      trend: portfolio && portfolio.total_gain_loss > 0 ? "up" as const : portfolio && portfolio.total_gain_loss < 0 ? "down" as const : "neutral" as const,
      icon: BriefcaseBusiness,
    },
    {
      title: "Today's Gain",
      value: isLoading ? "Loading..." : formatSignedCurrency(livePortfolio.todayGain),
      change: `${formatSignedPercent(livePortfolio.todayGainPercent)} intraday estimate`,
      trend: livePortfolio.todayGain > 0 ? "up" as const : livePortfolio.todayGain < 0 ? "down" as const : "neutral" as const,
      icon: BadgeDollarSign,
    },
    {
      title: "Watchlist Count",
      value: isLoading ? "Loading..." : String(watchlistCount ?? 0),
      change: `${watchlistCount ?? 0} unique symbols tracked`,
      trend: watchlistCount ? "up" as const : "neutral" as const,
      icon: Activity,
    },
    {
      title: "Market Overview",
      value: marketOverview.value,
      change: marketOverview.change,
      trend: marketOverview.trend,
      icon: BarChart3,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <MetricCard key={metric.title} {...metric} />
      ))}
    </div>
  );
}
