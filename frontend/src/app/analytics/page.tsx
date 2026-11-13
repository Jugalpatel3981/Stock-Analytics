import type { Metadata } from "next";

import { PortfolioAnalytics } from "@/components/analytics/portfolio-analytics";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { PageHeader } from "@/components/dashboard/page-header";
import { requireAuthenticatedUser } from "@/lib/auth-server";

export const metadata: Metadata = { title: "Analytics" };

export default async function AnalyticsPage() {
  const user = await requireAuthenticatedUser();

  return (
    <DashboardShell userName={user.name} activeItem="Analytics">
      <div className="space-y-5">
        <PageHeader title="Analytics" description="How your holdings perform against the S&P 500, how risky they are, and where your money is concentrated." />
        <PortfolioAnalytics />
      </div>
    </DashboardShell>
  );
}
