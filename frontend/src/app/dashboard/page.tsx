import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Newspaper } from "lucide-react";

import { DashboardMetrics } from "@/components/dashboard/dashboard-metrics";
import { DashboardNews } from "@/components/dashboard/dashboard-news";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { DashboardWatchlist } from "@/components/dashboard/dashboard-watchlist";
import { LiveMarketOverview } from "@/components/dashboard/live-market-overview";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AuthUser } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/env";

export const metadata: Metadata = { title: "Dashboard" };

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

        <SectionPanel
          title="Market Overview"
          description="Real-time market stream"
          action={<Badge variant="secondary">Finnhub Stream</Badge>}
        >
          <LiveMarketOverview />
        </SectionPanel>

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
            description="Latest headlines"
            action={<Newspaper className="h-5 w-5 text-primary" aria-hidden="true" />}
          >
            <DashboardNews />
          </SectionPanel>
        </div>

        <div className="rounded-md border bg-card/70 p-4 text-xs leading-5 text-muted-foreground">
          Market data is for informational and educational purposes only. Verify data, review risks, and make investment decisions independently.
        </div>
      </div>
    </DashboardShell>
  );
}
