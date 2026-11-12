"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast-provider";
import { getStockHistory, type HistoricalPricePoint, type StockHistoryRange } from "@/lib/api";
import { cn } from "@/lib/utils";

const ranges: Array<{ label: string; value: StockHistoryRange }> = [
  { label: "1 Day", value: "1d" },
  { label: "1 Week", value: "1wk" },
  { label: "1 Month", value: "1mo" },
  { label: "1 Year", value: "1y" },
];

type StockPriceChartProps = {
  ticker: string;
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatAxisLabel(timestamp: string, range: StockHistoryRange) {
  const date = new Date(timestamp);

  if (range === "1d") {
    return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  }

  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Open, high, low and close for the whole selected range, not just its last bar.
function summarizeRange(prices: HistoricalPricePoint[]) {
  if (prices.length === 0) {
    return null;
  }

  return {
    open: prices[0].open,
    high: Math.max(...prices.map((price) => price.high)),
    low: Math.min(...prices.map((price) => price.low)),
    close: prices[prices.length - 1].close,
  };
}

export function StockPriceChart({ ticker }: StockPriceChartProps) {
  const [selectedRange, setSelectedRange] = useState<StockHistoryRange>("1mo");
  const [prices, setPrices] = useState<HistoricalPricePoint[]>([]);
  const { showToast } = useToast();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isActive = true;

    async function loadHistory() {
      setIsLoading(true);

      try {
        const history = await getStockHistory(ticker, selectedRange);

        if (isActive) {
          setPrices(history.prices);
        }
      } catch (caughtError) {
        if (isActive) {
          setPrices([]);
          showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to load historical prices" });
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    loadHistory();

    return () => {
      isActive = false;
    };
  }, [selectedRange, showToast, ticker]);

  const chartData = useMemo(
    () =>
      prices.map((price) => ({
        ...price,
        label: formatAxisLabel(price.timestamp, selectedRange),
      })),
    [prices, selectedRange],
  );

  const summary = useMemo(() => summarizeRange(prices), [prices]);

  return (
    <section className="rounded-lg border bg-card/80">
      <div className="flex flex-col gap-4 border-b p-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-base font-semibold">Historical Price Chart</h2>
          <p className="mt-1 text-sm text-muted-foreground">Open, high, low and close for the selected period</p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex">
          {ranges.map((range) => (
            <Button
              key={range.value}
              size="sm"
              variant={selectedRange === range.value ? "default" : "outline"}
              onClick={() => setSelectedRange(range.value)}
              className="min-w-20"
            >
              {range.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="p-5">
        <div className="mb-4 grid gap-3 sm:grid-cols-4">
          {[
            { label: "Open", value: summary?.open },
            { label: "High", value: summary?.high },
            { label: "Low", value: summary?.low },
            { label: "Close", value: summary?.close },
          ].map((item) => (
            <div key={item.label} className="rounded-md border bg-background/40 p-3">
              <p className="text-xs font-medium uppercase text-muted-foreground">{item.label}</p>
              <p className="mt-2 text-lg font-semibold">{item.value ? formatCurrency(item.value) : "N/A"}</p>
            </div>
          ))}
        </div>

        <div className="h-[340px] rounded-md border bg-background/30 p-3">
          {isLoading ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading chart...</div>
          ) : prices.length === 0 ? (
            <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">No historical prices available.</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ left: 8, right: 8, top: 12, bottom: 0 }}>
                <defs>
                  <linearGradient id="closePrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.45} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  minTickGap={28}
                />
                <YAxis
                  domain={["dataMin", "dataMax"]}
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(value) => `$${Number(value).toFixed(0)}`}
                  width={56}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) {
                      return null;
                    }

                    const point = payload[0].payload as HistoricalPricePoint & { label: string };

                    return (
                      <div className="rounded-md border bg-card p-3 text-xs shadow-lg">
                        <p className="mb-2 font-medium">{label}</p>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-muted-foreground">
                          <span>Open</span>
                          <span className="text-right text-foreground">{formatCurrency(point.open)}</span>
                          <span>High</span>
                          <span className="text-right text-foreground">{formatCurrency(point.high)}</span>
                          <span>Low</span>
                          <span className="text-right text-foreground">{formatCurrency(point.low)}</span>
                          <span>Close</span>
                          <span className="text-right text-foreground">{formatCurrency(point.close)}</span>
                        </div>
                      </div>
                    );
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  fill="url(#closePrice)"
                  dot={false}
                  activeDot={{ r: 4, className: cn("fill-primary stroke-background") }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </section>
  );
}


