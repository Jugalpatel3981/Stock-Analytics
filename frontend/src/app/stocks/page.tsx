import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { PageHeader } from "@/components/dashboard/page-header";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { PopularLiveStocks } from "@/components/stocks/popular-live-stocks";
import { StockSearchForm } from "@/components/stocks/stock-search-form";
import { requireAuthenticatedUser } from "@/lib/auth-server";

export const metadata: Metadata = { title: "Stocks" };

export default async function StocksPage() {
  const user = await requireAuthenticatedUser();

  return (
    <DashboardShell userName={user.name} activeItem="Stocks">
      <div className="space-y-5">
        <PageHeader title="Stocks" description="Look up any US stock or ETF by company name or ticker." />
        <SectionPanel title="Search" description="Open a stock to see its chart, key figures and news.">
          <StockSearchForm />
        </SectionPanel>

        <SectionPanel title="Popular stocks" description="Live prices for widely followed companies.">
          <PopularLiveStocks />
        </SectionPanel>
      </div>
    </DashboardShell>
  );
}
