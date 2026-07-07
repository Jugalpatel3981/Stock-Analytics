import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { PopularLiveStocks } from "@/components/stocks/popular-live-stocks";
import { StockSearchForm } from "@/components/stocks/stock-search-form";
import { Badge } from "@/components/ui/badge";
import { requireAuthenticatedUser } from "@/lib/auth-server";

export default async function StocksPage() {
  const user = await requireAuthenticatedUser();

  return (
    <DashboardShell userName={user.name} activeItem="Stocks">
      <div className="space-y-5">
        <SectionPanel
          title="Stocks"
          description="Search Yahoo Finance by company name or ticker"
          action={<Badge variant="secondary">Yahoo Finance</Badge>}
        >
          <StockSearchForm />
        </SectionPanel>

        <SectionPanel title="Popular Tickers" description="Live prices, movement, and latest trade activity">
          <PopularLiveStocks />
        </SectionPanel>
      </div>
    </DashboardShell>
  );
}
