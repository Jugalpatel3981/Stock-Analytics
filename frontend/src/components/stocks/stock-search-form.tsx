"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useState } from "react";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { searchStocks, type StockSearchResult } from "@/lib/api";

export function StockSearchForm() {
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSearching(true);

    const formData = new FormData(event.currentTarget);
    const query = String(formData.get("query") ?? "").trim();

    try {
      const searchResults = await searchStocks(query);
      setResults(searchResults);
    } catch (caughtError) {
      setResults([]);
      setError(caughtError instanceof Error ? caughtError.message : "Unable to search ticker");
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <div className="space-y-4">
      <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleSubmit}>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <Input
            className="pl-9 uppercase"
            name="query"
            placeholder="Search ticker, e.g. NVDA"
            autoComplete="off"
            maxLength={12}
            required
          />
        </div>
        <Button type="submit" disabled={isSearching}>
          {isSearching ? "Searching..." : "Search"}
        </Button>
      </form>

      {error ? <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}

      {results.length > 0 ? (
        <div className="overflow-hidden rounded-md border">
          {results.map((stock) => (
            <Link
              key={stock.ticker}
              href={`/stocks/${stock.ticker}`}
              className="grid gap-3 border-b px-4 py-4 text-sm transition-colors last:border-b-0 hover:bg-secondary sm:grid-cols-[0.8fr_1.5fr_0.8fr_0.8fr]"
            >
              <span className="font-semibold">{stock.ticker}</span>
              <span className="text-muted-foreground">{stock.company_name ?? "Company unavailable"}</span>
              <span>{stock.current_price ? `$${stock.current_price.toFixed(2)}` : "N/A"}</span>
              <span className="text-muted-foreground">{stock.exchange ?? stock.currency ?? "Yahoo"}</span>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
