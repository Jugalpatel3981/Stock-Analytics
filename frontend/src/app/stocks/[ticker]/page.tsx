import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Building2, ExternalLink } from "lucide-react";

import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { SectionPanel } from "@/components/dashboard/section-panel";
import { LiveStockCard } from "@/components/market/live-stock-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StockPriceChart } from "@/components/stocks/stock-price-chart";
import { getAuthCookieHeader, requireAuthenticatedUser } from "@/lib/auth-server";
import type { StockDetail } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/env";

type StockDetailPageProps = {
  params: Promise<{
    ticker: string;
  }>;
};

function formatCurrency(value: number | null, currency: string | null) {
  if (value === null) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency ?? "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatNumber(value: number | null) {
  if (value === null) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US").format(value);
}

function formatLargeNumber(value: number | null) {
  if (value === null) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

async function getStockDetail(ticker: string): Promise<StockDetail> {
  const cookieHeader = await getAuthCookieHeader();
  const response = await fetch(`${getApiBaseUrl()}/stocks/${ticker}`, {
    headers: {
      Cookie: cookieHeader,
    },
    cache: "no-store",
  });

  if (response.status === 404) {
    notFound();
  }

  if (!response.ok) {
    throw new Error("Unable to load stock detail");
  }

  return response.json() as Promise<StockDetail>;
}

export default async function StockDetailPage({ params }: StockDetailPageProps) {
  const user = await requireAuthenticatedUser();
  const { ticker } = await params;
  const stock = await getStockDetail(ticker);

  const fundamentals = [
    { label: "Current Price", value: formatCurrency(stock.current_price, stock.currency) },
    { label: "Volume", value: formatNumber(stock.volume) },
    { label: "Market Cap", value: formatLargeNumber(stock.market_cap) },
    { label: "PE Ratio", value: stock.pe_ratio ? stock.pe_ratio.toFixed(2) : "N/A" },
  ];

  return (
    <DashboardShell userName={user.name} activeItem="Stocks">
      <div className="space-y-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Button variant="outline" size="sm" asChild>
            <Link href="/stocks">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to Stocks
            </Link>
          </Button>
          <Badge variant="secondary">{stock.data_source}</Badge>
        </div>

        <section className="rounded-lg border bg-card/80 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-md bg-primary text-primary-foreground">
                  <Building2 className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{stock.exchange ?? "Exchange unavailable"}</p>
                  <h1 className="text-3xl font-semibold tracking-normal">{stock.ticker}</h1>
                </div>
              </div>
              <p className="mt-4 max-w-3xl text-base text-muted-foreground">
                {stock.company_name ?? "Company name unavailable"}
              </p>
            </div>
            <LiveStockCard
              symbol={stock.ticker}
              company={stock.company_name}
              initialPrice={stock.current_price}
              initialVolume={stock.volume}
              currency={stock.currency}
            />
          </div>
        </section>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {fundamentals.map((item) => (
            <div key={item.label} className="rounded-lg border bg-card/80 p-4">
              <p className="text-xs font-medium uppercase text-muted-foreground">{item.label}</p>
              <p className="mt-3 text-2xl font-semibold tracking-normal">{item.value}</p>
            </div>
          ))}
        </div>

        <StockPriceChart ticker={stock.ticker} />

        <div className="grid gap-5 xl:grid-cols-[1fr_0.7fr]">
          <SectionPanel title="Company Information" description="Yahoo Finance company profile">
            <p className="text-sm leading-6 text-muted-foreground">
              {stock.business_summary ?? "Business summary is unavailable for this ticker."}
            </p>
          </SectionPanel>

          <SectionPanel title="Classification" description="Sector and industry metadata">
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3 border-b pb-3">
                <span className="text-muted-foreground">Sector</span>
                <span className="text-right font-medium">{stock.sector ?? "N/A"}</span>
              </div>
              <div className="flex items-center justify-between gap-3 border-b pb-3">
                <span className="text-muted-foreground">Industry</span>
                <span className="text-right font-medium">{stock.industry ?? "N/A"}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Website</span>
                {stock.website ? (
                  <a
                    href={stock.website}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-right font-medium text-primary hover:underline"
                  >
                    Visit
                    <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  </a>
                ) : (
                  <span className="font-medium">N/A</span>
                )}
              </div>
            </div>
          </SectionPanel>
        </div>

        <div className="rounded-md border bg-card/70 p-4 text-xs leading-5 text-muted-foreground">
          Market data is provided for informational and educational purposes only. Verify data before making investment decisions.
        </div>
      </div>
    </DashboardShell>
  );
}
