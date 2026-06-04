import { Activity, ArrowDownRight, ArrowUpRight, BrainCircuit, Database, LineChart, ShieldCheck } from "lucide-react";

import { AppHeader } from "@/components/layout/app-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getApiBaseUrl } from "@/lib/env";

const watchlist = [
  { symbol: "NVDA", name: "NVIDIA", price: "$1,178.42", change: "+2.14%", direction: "up" },
  { symbol: "MSFT", name: "Microsoft", price: "$472.19", change: "+0.62%", direction: "up" },
  { symbol: "AAPL", name: "Apple", price: "$203.77", change: "-0.44%", direction: "down" },
  { symbol: "AMZN", name: "Amazon", price: "$185.02", change: "+1.03%", direction: "up" },
];

const intelligenceCards = [
  {
    title: "Market Pulse",
    description: "AI-ready summary queue for macro, sector, and watchlist signals.",
    icon: Activity,
    value: "Stable",
  },
  {
    title: "Data Pipeline",
    description: "Backend foundation prepared for PostgreSQL-backed market data.",
    icon: Database,
    value: "Online",
  },
  {
    title: "Risk Review",
    description: "Portfolio risk workflows can be introduced in a future phase.",
    icon: ShieldCheck,
    value: "Pending",
  },
];

export default function Home() {
  const apiBaseUrl = getApiBaseUrl();

  return (
    <main className="min-h-screen">
      <AppHeader />
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
          <div className="rounded-lg border bg-card p-5 shadow-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <Badge variant="secondary">Phase 1 foundation</Badge>
                <h1 className="mt-3 text-3xl font-semibold tracking-normal text-foreground sm:text-4xl">
                  Portfolio Intelligence Dashboard
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
                  A production-ready baseline for stock research, market monitoring, and AI-assisted portfolio decisions.
                </p>
              </div>
              <Button className="w-full md:w-auto">
                <BrainCircuit className="h-4 w-4" aria-hidden="true" />
                Analyze
              </Button>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              {intelligenceCards.map((item) => (
                <div key={item.title} className="rounded-md border bg-background p-4">
                  <div className="flex items-center justify-between gap-3">
                    <item.icon className="h-5 w-5 text-primary" aria-hidden="true" />
                    <span className="text-xs font-medium text-muted-foreground">{item.value}</span>
                  </div>
                  <h2 className="mt-4 text-sm font-semibold">{item.title}</h2>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.description}</p>
                </div>
              ))}
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>API Connection</CardTitle>
              <CardDescription>Frontend environment wiring for the backend service.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border bg-muted/60 p-3 font-mono text-xs text-muted-foreground">
                {apiBaseUrl}
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                <LineChart className="h-4 w-4 text-primary" aria-hidden="true" />
                Ready for live health checks and stock endpoints.
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Watchlist</CardTitle>
              <CardDescription>Initial UI shell for future real-time quote data.</CardDescription>
            </div>
            <Button variant="outline" size="sm">Add Symbol</Button>
          </CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-md border">
              <div className="grid grid-cols-[0.8fr_1.2fr_1fr_1fr] bg-muted px-4 py-3 text-xs font-medium uppercase text-muted-foreground">
                <span>Symbol</span>
                <span>Company</span>
                <span>Price</span>
                <span className="text-right">Change</span>
              </div>
              {watchlist.map((stock) => {
                const isUp = stock.direction === "up";
                const Icon = isUp ? ArrowUpRight : ArrowDownRight;

                return (
                  <div
                    key={stock.symbol}
                    className="grid grid-cols-[0.8fr_1.2fr_1fr_1fr] items-center border-t px-4 py-4 text-sm"
                  >
                    <span className="font-semibold">{stock.symbol}</span>
                    <span className="text-muted-foreground">{stock.name}</span>
                    <span>{stock.price}</span>
                    <span className={`flex items-center justify-end gap-1 font-medium ${isUp ? "text-emerald-700" : "text-red-600"}`}>
                      <Icon className="h-4 w-4" aria-hidden="true" />
                      {stock.change}
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
