import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
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
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">Personal research lists</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">Watchlists</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Create focused lists of tickers, add stocks, and jump into detailed research pages.
          </p>
        </div>
        <WatchlistManager initialWatchlists={watchlists} />
      </div>
    </DashboardShell>
  );
}
