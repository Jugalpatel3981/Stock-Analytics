import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { PageHeader } from "@/components/dashboard/page-header";
import { PortfolioManager } from "@/components/portfolio/portfolio-manager";
import { getAuthCookieHeader, requireAuthenticatedUser } from "@/lib/auth-server";
import type { PortfolioGrowthResponse, PortfolioSummary } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/env";

export const metadata: Metadata = { title: "Portfolio" };

const EMPTY_SUMMARY: PortfolioSummary = {
  total_value: 0,
  total_cost: 0,
  total_gain_loss: 0,
  total_percentage_return: 0,
  unpriced_holdings: 0,
  holdings: [],
};

async function getPortfolioSummary(): Promise<PortfolioSummary> {
  const cookieHeader = await getAuthCookieHeader();
  const response = await fetch(`${getApiBaseUrl()}/portfolio/holdings`, {
    headers: {
      Cookie: cookieHeader,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Unable to load portfolio holdings");
  }

  return response.json() as Promise<PortfolioSummary>;
}

async function getPortfolioGrowth(): Promise<PortfolioGrowthResponse> {
  const cookieHeader = await getAuthCookieHeader();
  const response = await fetch(`${getApiBaseUrl()}/portfolio/growth`, {
    headers: {
      Cookie: cookieHeader,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Unable to load portfolio growth");
  }

  return response.json() as Promise<PortfolioGrowthResponse>;
}

export default async function PortfolioPage() {
  const user = await requireAuthenticatedUser();
  // Market data can be slow on free hosting. Render the page anyway and let the
  // client retry whatever failed, instead of showing a full-page error.
  const [summaryResult, growthResult] = await Promise.allSettled([
    getPortfolioSummary(),
    getPortfolioGrowth(),
  ]);
  const summary = summaryResult.status === "fulfilled" ? summaryResult.value : EMPTY_SUMMARY;
  const growth = growthResult.status === "fulfilled" ? growthResult.value.points : [];
  const needsReload = summaryResult.status === "rejected" || growthResult.status === "rejected";

  return (
    <DashboardShell userName={user.name} activeItem="Portfolio">
      <div className="space-y-5">
        <PageHeader title="Portfolio" description="Track what you own, with live value, gain and loss." />
        <PortfolioManager initialSummary={summary} initialGrowth={growth} reloadOnMount={needsReload} />
      </div>
    </DashboardShell>
  );
}
