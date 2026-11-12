import type { Metadata } from "next";

import { StockCompare } from "@/components/compare/stock-compare";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { requireAuthenticatedUser } from "@/lib/auth-server";

export const metadata: Metadata = { title: "Compare" };

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA"];
const MAX_SYMBOLS = 5;

type ComparePageProps = {
  searchParams?: Promise<{ symbols?: string | string[] }>;
};

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const user = await requireAuthenticatedUser();
  const resolvedSearchParams = await searchParams;
  const symbolsParam = Array.isArray(resolvedSearchParams?.symbols)
    ? resolvedSearchParams?.symbols[0]
    : resolvedSearchParams?.symbols;
  const requestedSymbols = Array.from(
    new Set((symbolsParam ?? "").split(",").map((symbol) => symbol.trim().toUpperCase()).filter(Boolean)),
  ).slice(0, MAX_SYMBOLS);

  return (
    <DashboardShell userName={user.name} activeItem="Compare">
      <div className="space-y-5">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">Side-by-side research</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">Compare stocks</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Put two to five stocks on one chart, compare their return and risk, and see how closely they move together.
          </p>
        </div>
        <StockCompare initialSymbols={requestedSymbols.length > 0 ? requestedSymbols : DEFAULT_SYMBOLS} />
      </div>
    </DashboardShell>
  );
}
