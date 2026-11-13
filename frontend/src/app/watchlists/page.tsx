import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { PageHeader } from "@/components/dashboard/page-header";
import { WatchlistManager } from "@/components/watchlists/watchlist-manager";
import { getAuthCookieHeader, requireAuthenticatedUser } from "@/lib/auth-server";
import type { Watchlist } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/env";

export const metadata: Metadata = { title: "Watchlists" };

async function getWatchlists(): Promise<Watchlist[]> {
  const cookieHeader = await getAuthCookieHeader();
  const response = await fetch(`${getApiBaseUrl()}/watchlists`, {
    headers: {
      Cookie: cookieHeader,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Unable to load watchlists");
  }

  return response.json() as Promise<Watchlist[]>;
}

export default async function WatchlistsPage() {
  const user = await requireAuthenticatedUser();
  const watchlists = await getWatchlists();

  return (
    <DashboardShell userName={user.name} activeItem="Watchlists">
      <div className="space-y-5">
        <PageHeader title="Watchlists" description="Group the stocks you want to follow and see their live prices." />
        <WatchlistManager initialWatchlists={watchlists} />
      </div>
    </DashboardShell>
  );
}
