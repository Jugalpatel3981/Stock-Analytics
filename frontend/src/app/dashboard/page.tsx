import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Newspaper, Sparkles } from "lucide-react";

import { DashboardMetrics } from "@/components/dashboard/dashboard-metrics";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { DashboardWatchlist } from "@/components/dashboard/dashboard-watchlist";
import { LiveMarketOverview } from "@/components/dashboard/live-market-overview";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { StockPredictionCard } from "@/components/dashboard/stock-prediction-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AuthUser } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/env";


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
        <DashboardMetrics />

        <div className="grid gap-5 xl:grid-cols-[1.55fr_0.85fr]">
          <SectionPanel
            title="Market Overview"
            description="Real-time market stream"
            action={<Badge variant="secondary">Finnhub Stream</Badge>}
          >
            <LiveMarketOverview />
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
            <DashboardWatchlist />
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
