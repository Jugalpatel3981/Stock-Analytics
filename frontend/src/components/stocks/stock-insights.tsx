"use client";

import { useEffect, useState } from "react";

import { SectionPanel } from "@/components/dashboard/section-panel";
import { getStockInsights, type StockInsights as StockInsightsData } from "@/lib/analytics-api";
import { formatCurrency, formatDate, formatNumber, formatPercent, formatSignedPercent } from "@/lib/format";

type StockInsightsProps = {
  ticker: string;
};

type Ratings = NonNullable<StockInsightsData["analyst_ratings"]>;

// Buy-side ratings in blue, sell-side in red, hold in neutral grey.
const ratingSegments: Array<{ key: keyof Omit<Ratings, "period">; label: string; color: string }> = [
  { key: "strong_buy", label: "Strong buy", color: "#3987e5" },
  { key: "buy", label: "Buy", color: "#86b6ef" },
  { key: "hold", label: "Hold", color: "#6b7280" },
  { key: "sell", label: "Sell", color: "#f2a3a3" },
  { key: "strong_sell", label: "Strong sell", color: "#e66767" },
];

function AnalystRatings({ ratings }: { ratings: Ratings }) {
  const total = ratingSegments.reduce((sum, segment) => sum + ratings[segment.key], 0);
  const buyShare = (ratings.strong_buy + ratings.buy) / total;

  return (
    <div>
      <p className="text-sm">
        <span className="text-2xl font-semibold">{formatPercent(buyShare, 0)}</span>{" "}
        <span className="text-muted-foreground">
          of {total} analysts rate it a buy{ratings.period ? ` (${formatDate(ratings.period, { month: "short", year: "numeric" })})` : ""}
        </span>
      </p>
      <div className="mt-3 flex h-3 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={`Analyst ratings: ${ratingSegments.map((segment) => `${ratings[segment.key]} ${segment.label.toLowerCase()}`).join(", ")}`}>
        {ratingSegments
          .filter((segment) => ratings[segment.key] > 0)
          .map((segment) => (
            <div
              key={segment.key}
              style={{ width: `${(ratings[segment.key] / total) * 100}%`, backgroundColor: segment.color }}
              title={`${segment.label}: ${ratings[segment.key]}`}
            />
          ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {ratingSegments.map((segment) => (
          <li key={segment.key} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: segment.color }} aria-hidden="true" />
            {segment.label} <span className="font-medium text-foreground">{ratings[segment.key]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FiftyTwoWeekRange({ low, high, current }: { low: number; high: number; current: number | null }) {
  const position = current === null || high <= low ? null : Math.min(1, Math.max(0, (current - low) / (high - low)));

  return (
    <div>
      <div className="flex items-baseline justify-between text-sm">
        <span>
          <span className="text-muted-foreground">Low</span> <span className="font-medium">{formatCurrency(low)}</span>
        </span>
        <span>
          <span className="text-muted-foreground">High</span> <span className="font-medium">{formatCurrency(high)}</span>
        </span>
      </div>
      <div className="relative mt-2 h-2 rounded-full bg-secondary">
        {position !== null ? (
          <div
            className="absolute top-1/2 h-4 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary ring-2 ring-card"
            style={{ left: `${position * 100}%` }}
            title={`Current price ${formatCurrency(current)}`}
          />
        ) : null}
      </div>
      {position !== null ? (
        <p className="mt-2 text-xs text-muted-foreground">
          The current price of {formatCurrency(current)} is {formatPercent(position, 0)} of the way from the 52-week low to the high.
        </p>
      ) : null}
    </div>
  );
}

export function StockInsights({ ticker, currentPrice }: StockInsightsProps & { currentPrice: number | null }) {
  const [insights, setInsights] = useState<StockInsightsData | null>(null);
  const [hasFailed, setHasFailed] = useState(false);

  useEffect(() => {
    let isActive = true;

    getStockInsights(ticker)
      .then((result) => {
        if (isActive) {
          setInsights(result);
        }
      })
      .catch(() => {
        if (isActive) {
          setHasFailed(true);
        }
      });

    return () => {
      isActive = false;
    };
  }, [ticker]);

  if (hasFailed) {
    return (
      <SectionPanel title="Analyst view and key figures" description="Ratings, earnings and yearly range">
        <p className="text-sm text-muted-foreground">This information could not be loaded right now.</p>
      </SectionPanel>
    );
  }

  if (insights === null) {
    return (
      <SectionPanel title="Analyst view and key figures" description="Ratings, earnings and yearly range">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </SectionPanel>
    );
  }

  const { analyst_ratings: ratings, next_earnings: earnings, key_metrics: metrics } = insights;
  if (!insights.available || (!ratings && !earnings && !metrics)) {
    return null;
  }

  const figures = metrics
    ? [
        { label: "Dividend yield", value: formatPercent(metrics.dividend_yield, 2) },
        { label: "Earnings per share (12 months)", value: formatCurrency(metrics.eps_ttm) },
        { label: "Net profit margin", value: formatPercent(metrics.net_margin) },
        { label: "Revenue growth (year on year)", value: formatSignedPercent(metrics.revenue_growth_yoy) },
        { label: "Beta", value: formatNumber(metrics.beta) },
      ].filter((figure) => figure.value !== "N/A")
    : [];

  return (
    <SectionPanel title="Analyst view and key figures" description={`Ratings, earnings and yearly range from ${insights.data_source}`}>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-2">
          <h3 className="text-xs font-medium uppercase text-muted-foreground">Analyst ratings</h3>
          {ratings ? <AnalystRatings ratings={ratings} /> : <p className="text-sm text-muted-foreground">Not covered by analysts.</p>}
        </div>

        <div className="space-y-2">
          <h3 className="text-xs font-medium uppercase text-muted-foreground">52-week range</h3>
          {metrics?.week_52_low != null && metrics.week_52_high != null ? (
            <FiftyTwoWeekRange low={metrics.week_52_low} high={metrics.week_52_high} current={currentPrice} />
          ) : (
            <p className="text-sm text-muted-foreground">Unavailable.</p>
          )}
          <h3 className="pt-3 text-xs font-medium uppercase text-muted-foreground">Next earnings report</h3>
          {earnings ? (
            <p className="text-sm">
              <span className="font-medium">{formatDate(earnings.date)}</span>
              {earnings.eps_estimate !== null ? (
                <span className="text-muted-foreground"> · expected earnings per share {formatCurrency(earnings.eps_estimate)}</span>
              ) : null}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">No report scheduled in the next four months.</p>
          )}
        </div>

        <div className="space-y-2">
          <h3 className="text-xs font-medium uppercase text-muted-foreground">Key figures</h3>
          {figures.length > 0 ? (
            <dl className="space-y-2 text-sm">
              {figures.map((figure) => (
                <div key={figure.label} className="flex items-center justify-between gap-3 border-b pb-2 last:border-b-0">
                  <dt className="text-muted-foreground">{figure.label}</dt>
                  <dd className="font-medium">{figure.value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-muted-foreground">Unavailable.</p>
          )}
        </div>
      </div>
    </SectionPanel>
  );
}
