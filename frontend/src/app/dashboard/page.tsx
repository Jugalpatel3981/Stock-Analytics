import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BadgeDollarSign,
  BarChart3,
  BriefcaseBusiness,
  Newspaper,
  Sparkles,
} from "lucide-react";

import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { MetricCard } from "@/components/dashboard/metric-card";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { StockPredictionCard } from "@/components/dashboard/stock-prediction-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AuthUser } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/env";

const metrics = [
  {
    title: "Portfolio Value",
    value: "$128,430.27",
    change: "+$2,184.12 all time",
    trend: "up" as const,
    icon: BriefcaseBusiness,
  },
  {
    title: "Today's Gain",
    value: "+$842.18",
    change: "+0.66% intraday",
    trend: "up" as const,
    icon: BadgeDollarSign,
  },
  {
    title: "Watchlist Count",
    value: "18",
    change: "5 symbols active today",
    trend: "neutral" as const,
    icon: Activity,
  },
  {
    title: "Market Overview",
    value: "Risk-On",
    change: "Technology leading",
    trend: "up" as const,
    icon: BarChart3,
  },
];

const indices = [
  { label: "S&P 500", value: "6,094.28", change: "+0.42%", trend: "up" },
  { label: "Nasdaq", value: "19,812.44", change: "+0.71%", trend: "up" },
  { label: "Dow", value: "44,318.21", change: "-0.08%", trend: "down" },
  { label: "VIX", value: "14.82", change: "-2.11%", trend: "down" },
];

const watchlist = [
  { symbol: "NVDA", company: "NVIDIA", price: "$1,178.42", change: "+2.14%", volume: "48.2M", signal: "Momentum" },
  { symbol: "MSFT", company: "Microsoft", price: "$472.19", change: "+0.62%", volume: "21.8M", signal: "Quality" },
  { symbol: "AAPL", company: "Apple", price: "$203.77", change: "-0.44%", volume: "35.1M", signal: "Review" },
  { symbol: "AMZN", company: "Amazon", price: "$185.02", change: "+1.03%", volume: "29.4M", signal: "Growth" },
  { symbol: "JPM", company: "JPMorgan Chase", price: "$218.64", change: "-0.18%", volume: "9.7M", signal: "Value" },
];

const newsItems = [
  { source: "Market Desk", title: "Semiconductors lead early session gains", time: "12 min ago" },
  { source: "Earnings Watch", title: "Mega-cap technology earnings remain in focus", time: "34 min ago" },
  { source: "Macro Brief", title: "Treasury yields steady ahead of inflation data", time: "1 hr ago" },
];

async function getCurrentUser(): Promise<AuthUser> {
  const cookieHeader = (await cookies()).toString();

  if (!cookieHeader) {
    redirect("/login");
  }

  const response = await fetch(`${getApiBaseUrl()}/auth/me`, {
    headers: {
      Cookie: cookieHeader,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    redirect("/login");
  }

  return response.json() as Promise<AuthUser>;
}

export default async function DashboardPage() {
  const user = await getCurrentUser();

  return (
    <DashboardShell userName={user.name}>
      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <MetricCard key={metric.title} {...metric} />
          ))}
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.55fr_0.85fr]">
          <SectionPanel
            title="Market Overview"
            description="Major indices and volatility snapshot"
            action={<Badge variant="secondary">Live shell</Badge>}
          >
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {indices.map((index) => {
                const isUp = index.trend === "up";
                const Icon = isUp ? ArrowUpRight : ArrowDownRight;

                return (
                  <div key={index.label} className="rounded-md border bg-background/40 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-muted-foreground">{index.label}</p>
                      <Icon className={isUp ? "h-4 w-4 text-emerald-400" : "h-4 w-4 text-red-400"} aria-hidden="true" />
                    </div>
                    <p className="mt-4 text-xl font-semibold">{index.value}</p>
                    <p className={isUp ? "mt-1 text-sm text-emerald-400" : "mt-1 text-sm text-red-400"}>{index.change}</p>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 h-48 rounded-md border bg-[linear-gradient(180deg,hsl(var(--secondary))_0%,hsl(var(--background))_100%)] p-4">
              <div className="flex h-full items-end gap-2">
                {[44, 58, 51, 66, 72, 63, 78, 86, 81, 92, 88, 96].map((height, index) => (
                  <div
                    key={index}
                    className="min-w-0 flex-1 rounded-t bg-primary/70"
                    style={{ height: `${height}%` }}
                  />
                ))}
              </div>
            </div>
          </SectionPanel>

          <div className="space-y-5">
            <SectionPanel
              title="Stock Prediction"
              description="XGBoost next-close estimate"
              action={<Badge variant="secondary">ML Signal</Badge>}
            >
              <StockPredictionCard />
            </SectionPanel>

            <SectionPanel
              title="AI Assistant"
              description="Research support, not financial advice"
              action={<Sparkles className="h-5 w-5 text-primary" aria-hidden="true" />}
            >
              <div className="rounded-md border bg-background/40 p-4">
                <p className="text-sm leading-6 text-muted-foreground">
                  Portfolio is currently concentrated in technology. Review sector exposure, valuation risk, and upcoming earnings before making investment decisions.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge variant="secondary">Informational</Badge>
                  <Badge variant="outline">Confidence: Medium</Badge>
                </div>
              </div>
              <Button className="mt-4 w-full" variant="secondary" asChild>
                <Link href="/assistant">
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                  Open Assistant
                </Link>
              </Button>
            </SectionPanel>
          </div>
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <SectionPanel
            title="Watchlist"
            description="Priority symbols for today"
            action={(
              <Button size="sm" variant="outline" asChild>
                <Link href="/watchlists">Manage Lists</Link>
              </Button>
            )}
          >
            <div className="overflow-x-auto rounded-md border">
              <div className="min-w-[720px]">
                <div className="grid grid-cols-[0.7fr_1.2fr_0.9fr_0.8fr_0.8fr_0.9fr] bg-secondary px-4 py-3 text-xs font-medium uppercase text-muted-foreground">
                  <span>Symbol</span>
                  <span>Company</span>
                  <span>Price</span>
                  <span>Change</span>
                  <span>Volume</span>
                  <span className="text-right">Signal</span>
                </div>
                {watchlist.map((stock) => {
                  const isUp = stock.change.startsWith("+");

                  return (
                    <div
                      key={stock.symbol}
                      className="grid grid-cols-[0.7fr_1.2fr_0.9fr_0.8fr_0.8fr_0.9fr] items-center border-t px-4 py-4 text-sm"
                    >
                      <Link className="font-semibold text-primary hover:underline" href={`/stocks/${stock.symbol}`}>
                        {stock.symbol}
                      </Link>
                      <span className="text-muted-foreground">{stock.company}</span>
                      <span>{stock.price}</span>
                      <span className={isUp ? "font-medium text-emerald-400" : "font-medium text-red-400"}>{stock.change}</span>
                      <span className="text-muted-foreground">{stock.volume}</span>
                      <span className="text-right">
                        <Badge variant={stock.signal === "Review" ? "outline" : "secondary"}>{stock.signal}</Badge>
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </SectionPanel>

          <SectionPanel
            title="News"
            description="Source-backed market context"
            action={<Newspaper className="h-5 w-5 text-primary" aria-hidden="true" />}
          >
            <div className="space-y-3">
              {newsItems.map((item) => (
                <article key={item.title} className="rounded-md border bg-background/40 p-4">
                  <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                    <span>{item.source}</span>
                    <span>{item.time}</span>
                  </div>
                  <h2 className="mt-2 text-sm font-medium leading-5">{item.title}</h2>
                </article>
              ))}
            </div>
          </SectionPanel>
        </div>

        <div className="rounded-md border bg-card/70 p-4 text-xs leading-5 text-muted-foreground">
          AI summaries are for informational and educational purposes only. Verify data, review risks, and make investment decisions independently.
        </div>
      </div>
    </DashboardShell>
  );
}
