"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { IndexedLineChart } from "@/components/charts/indexed-line-chart";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { Button } from "@/components/ui/button";
import {
  getPortfolioAnalytics,
  type AllocationSlice,
  type PortfolioAnalytics as PortfolioAnalyticsData,
  type RiskMetrics,
} from "@/lib/analytics-api";
import { SERIES_COLORS } from "@/lib/chart-colors";
import {
  changeColor,
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
  formatSignedPercent,
} from "@/lib/format";
import { cn } from "@/lib/utils";

const BENCHMARK_NAME = "S&P 500";

type StatTileProps = {
  label: string;
  value: string;
  detail?: string;
  tone?: number | null;
};

function StatTile({ label, value, detail, tone }: StatTileProps) {
  return (
    <div className="rounded-lg border bg-card/80 p-4">
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className={cn("mt-3 text-2xl font-semibold tracking-normal", tone !== undefined && changeColor(tone))}>{value}</p>
      {detail ? <p className="mt-2 text-xs leading-5 text-muted-foreground">{detail}</p> : null}
    </div>
  );
}

function AllocationBars({ slices, emptyMessage }: { slices: AllocationSlice[]; emptyMessage: string }) {
  if (slices.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <ul className="space-y-3">
      {slices.map((slice) => (
        <li key={slice.label}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="font-medium">{slice.label}</span>
            <span className="text-muted-foreground">
              {formatCurrency(slice.value, 0)} · <span className="font-medium text-foreground">{formatPercent(slice.weight)}</span>
            </span>
          </div>
          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-secondary" title={`${slice.label}: ${formatPercent(slice.weight)}`}>
            <div
              className="h-full rounded-full"
              style={{ width: `${Math.max(slice.weight * 100, 1)}%`, backgroundColor: SERIES_COLORS[0] }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

type RiskRow = {
  label: string;
  explanation: string;
  portfolio: string;
  benchmark: string;
};

function buildRiskRows(portfolio: RiskMetrics, benchmark: RiskMetrics, beta: number | null, riskFreeRate: number): RiskRow[] {
  return [
    {
      label: "Return",
      explanation: "Change in value over the period.",
      portfolio: formatSignedPercent(portfolio.total_return),
      benchmark: formatSignedPercent(benchmark.total_return),
    },
    {
      label: "Volatility",
      explanation: "How much the value swings from day to day, scaled to a year. Higher means a bumpier ride.",
      portfolio: formatPercent(portfolio.volatility),
      benchmark: formatPercent(benchmark.volatility),
    },
    {
      label: "Sharpe ratio",
      explanation: `Return earned above a ${formatPercent(riskFreeRate, 0)} risk-free rate for each unit of volatility. Higher is better; above 1 is good.`,
      portfolio: formatNumber(portfolio.sharpe_ratio),
      benchmark: formatNumber(benchmark.sharpe_ratio),
    },
    {
      label: "Max drawdown",
      explanation: "The largest fall from a peak to a later low during the period.",
      portfolio: formatPercent(portfolio.max_drawdown),
      benchmark: formatPercent(benchmark.max_drawdown),
    },
    {
      label: "Best day",
      explanation: "The largest one-day gain.",
      portfolio: formatSignedPercent(portfolio.best_day),
      benchmark: formatSignedPercent(benchmark.best_day),
    },
    {
      label: "Worst day",
      explanation: "The largest one-day loss.",
      portfolio: formatSignedPercent(portfolio.worst_day),
      benchmark: formatSignedPercent(benchmark.worst_day),
    },
    {
      label: "Beta",
      explanation: `How strongly the portfolio moves with the ${BENCHMARK_NAME}. 1.2 means it tends to move 1.2% when the market moves 1%.`,
      portfolio: formatNumber(beta),
      benchmark: "1.00",
    },
  ];
}

export function PortfolioAnalytics() {
  const [analytics, setAnalytics] = useState<PortfolioAnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    getPortfolioAnalytics()
      .then((result) => {
        if (isActive) {
          setAnalytics(result);
        }
      })
      .catch((caughtError: unknown) => {
        if (isActive) {
          setError(caughtError instanceof Error ? caughtError.message : "Unable to load portfolio analytics");
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  if (error) {
    return <p className="rounded-lg border bg-card/80 p-6 text-sm text-muted-foreground">{error}</p>;
  }

  if (analytics === null) {
    return <p className="rounded-lg border bg-card/80 p-6 text-sm text-muted-foreground">Analysing your portfolio...</p>;
  }

  if (analytics.holdings.length === 0) {
    return (
      <div className="rounded-lg border bg-card/80 p-8 text-center">
        <h2 className="text-lg font-semibold">Nothing to analyse yet</h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
          {analytics.warnings[0] ?? "Add holdings to your portfolio to see how they perform against the market."}
        </p>
        <Button className="mt-5" asChild>
          <Link href="/portfolio">Go to portfolio</Link>
        </Button>
      </div>
    );
  }

  const comparison = analytics.since_purchase;
  const excessReturn =
    comparison?.portfolio_return != null && comparison.benchmark_return != null
      ? comparison.portfolio_return - comparison.benchmark_return
      : null;
  const period =
    analytics.window_start && analytics.window_end
      ? `${formatDate(analytics.window_start)} to ${formatDate(analytics.window_end)}`
      : "the past year";
  const riskRows = buildRiskRows(analytics.portfolio, analytics.benchmark, analytics.beta, analytics.risk_free_rate);

  return (
    <div className="space-y-5">
      {analytics.warnings.length > 0 ? (
        <ul className="space-y-2">
          {analytics.warnings.map((warning) => (
            <li key={warning} className="flex items-start gap-3 rounded-lg border border-amber-400/30 bg-amber-400/5 p-4 text-sm">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" aria-hidden="true" />
              <span>{warning}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Invested"
          value={formatCurrency(comparison?.invested)}
          detail="What you paid for your current holdings."
        />
        <StatTile
          label="Value now"
          value={formatCurrency(comparison?.portfolio_value)}
          detail={`Return since purchase: ${formatSignedPercent(comparison?.portfolio_return)}`}
        />
        <StatTile
          label={`Same money in the ${BENCHMARK_NAME}`}
          value={formatCurrency(comparison?.benchmark_value)}
          detail={`Return over the same dates: ${formatSignedPercent(comparison?.benchmark_return)}`}
        />
        <StatTile
          label={`Versus the ${BENCHMARK_NAME}`}
          value={excessReturn === null ? "N/A" : `${formatSignedPercent(excessReturn)} pts`}
          tone={excessReturn}
          detail={
            excessReturn === null
              ? "The comparison is unavailable for these holdings."
              : excessReturn >= 0
                ? "Your picks beat the market since you bought them."
                : "The market did better than your picks since you bought them."
          }
        />
      </div>

      <SectionPanel
        title={`Your holdings against the ${BENCHMARK_NAME}`}
        description={`How today's holdings would have performed if held from ${period}. Both lines start at 0%.`}
      >
        <IndexedLineChart
          points={analytics.performance}
          series={[
            { key: "portfolio", label: "Your portfolio", color: SERIES_COLORS[0] },
            { key: "benchmark", label: `${BENCHMARK_NAME} (${analytics.benchmark_symbol})`, color: SERIES_COLORS[1] },
          ]}
          emptyMessage="Not enough shared price history to draw this chart yet."
        />
      </SectionPanel>

      <SectionPanel title="Risk and return" description={`Measured over ${period}, using daily closing prices.`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Measure</th>
                <th className="px-4 py-2 text-right font-medium">Portfolio</th>
                <th className="py-2 pl-4 text-right font-medium">{BENCHMARK_NAME}</th>
              </tr>
            </thead>
            <tbody>
              {riskRows.map((row) => (
                <tr key={row.label} className="border-b last:border-b-0">
                  <td className="py-3 pr-4">
                    <p className="font-medium">{row.label}</p>
                    <p className="mt-0.5 max-w-md text-xs leading-5 text-muted-foreground">{row.explanation}</p>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right align-top font-semibold">{row.portfolio}</td>
                  <td className="whitespace-nowrap py-3 pl-4 text-right align-top text-muted-foreground">{row.benchmark}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionPanel>

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionPanel title="Allocation by stock" description="Share of your portfolio's current value.">
          <AllocationBars slices={analytics.allocation_by_holding} emptyMessage="No priced holdings." />
        </SectionPanel>
        <SectionPanel title="Allocation by sector" description="How concentrated your portfolio is.">
          <AllocationBars slices={analytics.allocation_by_sector} emptyMessage="Sector information is unavailable." />
        </SectionPanel>
      </div>

      <SectionPanel
        title="Each holding since you bought it"
        description={`Best performers first. "${BENCHMARK_NAME}" is what the same money would have returned in the index over the same dates.`}
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="border-b text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Stock</th>
                <th className="px-4 py-2 text-right font-medium">Cost</th>
                <th className="px-4 py-2 text-right font-medium">Value</th>
                <th className="px-4 py-2 text-right font-medium">Gain / loss</th>
                <th className="px-4 py-2 text-right font-medium">Return</th>
                <th className="px-4 py-2 text-right font-medium">{BENCHMARK_NAME}</th>
                <th className="py-2 pl-4 text-right font-medium">Difference</th>
              </tr>
            </thead>
            <tbody>
              {analytics.holdings.map((holding) => (
                <tr key={holding.symbol} className="border-b last:border-b-0">
                  <td className="py-3 pr-4">
                    <Link className="font-semibold text-primary hover:underline" href={`/stocks/${holding.symbol}`}>
                      {holding.symbol}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right">{formatCurrency(holding.cost_basis)}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(holding.value)}</td>
                  <td className={cn("px-4 py-3 text-right font-medium", changeColor(holding.gain))}>{formatCurrency(holding.gain)}</td>
                  <td className={cn("px-4 py-3 text-right font-medium", changeColor(holding.return_since_purchase))}>
                    {formatSignedPercent(holding.return_since_purchase)}
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground">{formatSignedPercent(holding.benchmark_return)}</td>
                  <td className={cn("py-3 pl-4 text-right font-medium", changeColor(holding.excess_return))}>
                    {holding.excess_return === null ? "N/A" : `${formatSignedPercent(holding.excess_return)} pts`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionPanel>

      <p className="rounded-md border bg-card/70 p-4 text-xs leading-5 text-muted-foreground">
        Returns are price returns and do not include dividends, fees or taxes. Past performance does not predict future
        results. For informational and educational purposes only.
      </p>
    </div>
  );
}
