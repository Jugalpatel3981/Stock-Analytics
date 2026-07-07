import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { StockNewsFeed } from "@/components/news/stock-news-feed";
import { Badge } from "@/components/ui/badge";
import { requireAuthenticatedUser } from "@/lib/auth-server";

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
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">Market headlines</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">News</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Filter financial headlines by ticker to understand recent company-specific context.
          </p>
        </div>

        <SectionPanel
          title="Stock News"
          description="Yahoo Finance headlines filtered by ticker"
          action={<Badge variant="secondary">Informational</Badge>}
        >
          <StockNewsFeed initialTicker={initialTicker} />
        </SectionPanel>
      </div>
    </DashboardShell>
  );
}
