import type { Metadata } from "next";

import { PortfolioAnalytics } from "@/components/analytics/portfolio-analytics";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { requireAuthenticatedUser } from "@/lib/auth-server";

export const metadata: Metadata = { title: "Analytics" };

export default async function AnalyticsPage() {
  const user = await requireAuthenticatedUser();

  return (
    <DashboardShell userName={user.name} activeItem="Analytics">
      <div className="space-y-5">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">Portfolio analysis</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">Analytics</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            See how your holdings have performed against the S&amp;P 500, how risky they are, and where your money is
            concentrated.
          </p>
        </div>
        <PortfolioAnalytics />
      </div>
    </DashboardShell>
  );
}
