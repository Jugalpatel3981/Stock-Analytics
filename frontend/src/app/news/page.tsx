import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { PageHeader } from "@/components/dashboard/page-header";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { StockNewsFeed } from "@/components/news/stock-news-feed";
import { requireAuthenticatedUser } from "@/lib/auth-server";

export const metadata: Metadata = { title: "News" };

type NewsPageProps = {
  searchParams?: Promise<{ ticker?: string | string[] }>;
};

export default async function NewsPage({ searchParams }: NewsPageProps) {
  const user = await requireAuthenticatedUser();
  const resolvedSearchParams = await searchParams;
  const tickerParam = Array.isArray(resolvedSearchParams?.ticker)
    ? resolvedSearchParams?.ticker[0]
    : resolvedSearchParams?.ticker;
  const initialTicker = tickerParam?.trim().toUpperCase() || "NVDA";

  return (
    <DashboardShell userName={user.name} activeItem="News">
      <div className="space-y-5">
        <PageHeader title="News" description="Recent headlines for any stock." />

        <SectionPanel title="Headlines" description="From the past week, newest first.">
          <StockNewsFeed initialTicker={initialTicker} />
        </SectionPanel>
      </div>
    </DashboardShell>
  );
}
