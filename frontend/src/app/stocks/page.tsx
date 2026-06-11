import Link from "next/link";

import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { StockSearchForm } from "@/components/stocks/stock-search-form";
import { Badge } from "@/components/ui/badge";
import { requireAuthenticatedUser } from "@/lib/auth-server";

const popularTickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM"];

export default async function StocksPage() {
  const user = await requireAuthenticatedUser();

  return (
    <DashboardShell userName={user.name} activeItem="Stocks">
      <div className="space-y-5">
        <SectionPanel
          title="Stocks"
          description="Search Yahoo Finance by ticker"
          action={<Badge variant="secondary">Yahoo Finance</Badge>}
        >
          <StockSearchForm />
        </SectionPanel>

        <SectionPanel title="Popular Tickers" description="Quick starting points for market research">
          <div className="flex flex-wrap gap-2">
            {popularTickers.map((ticker) => (
              <Link
                key={ticker}
                href={`/stocks/${ticker}`}
                className="rounded-md border bg-background/40 px-3 py-2 text-sm font-medium transition-colors hover:bg-secondary"
              >
                {ticker}
              </Link>
            ))}
          </div>
        </SectionPanel>
      </div>
    </DashboardShell>
  );
}
