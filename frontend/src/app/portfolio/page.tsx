import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { PortfolioManager } from "@/components/portfolio/portfolio-manager";
import { getAuthCookieHeader, requireAuthenticatedUser } from "@/lib/auth-server";
import type { PortfolioGrowthResponse, PortfolioSummary } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/env";

export const metadata: Metadata = { title: "Portfolio" };

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
  const [summary, growth] = await Promise.all([
    getPortfolioSummary(),
    getPortfolioGrowth(),
  ]);

  return (
    <DashboardShell userName={user.name} activeItem="Portfolio">
      <div className="space-y-5">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">Owned positions</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">Portfolio</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Add holdings, monitor current value, and review gain/loss using live market prices.
          </p>
        </div>
        <PortfolioManager initialSummary={summary} initialGrowth={growth.points} />
      </div>
    </DashboardShell>
  );
}
