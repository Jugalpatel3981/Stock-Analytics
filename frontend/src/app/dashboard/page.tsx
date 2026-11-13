import type { Metadata } from "next";

import { DashboardNews } from "@/components/dashboard/dashboard-news";
import { DashboardOverview } from "@/components/dashboard/dashboard-overview";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { PageHeader } from "@/components/dashboard/page-header";
import { requireAuthenticatedUser } from "@/lib/auth-server";

export const metadata: Metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const user = await requireAuthenticatedUser();
  const firstName = user.name.trim().split(/\s+/)[0];

  return (
    <DashboardShell userName={user.name} activeItem="Dashboard">
      <div className="space-y-6">
        <PageHeader title="Dashboard" description={`Welcome back, ${firstName}. Here is how your portfolio and watchlist are doing.`} />
        <DashboardOverview aside={<DashboardNews />} />
        <p className="text-xs leading-5 text-muted-foreground">
          Market data is for informational and educational purposes only. It is not financial advice.
        </p>
      </div>
    </DashboardShell>
  );
}
