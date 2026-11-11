"use client";

import { ExternalLink, Newspaper, Search, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast-provider";
import { searchStocks, type StockSearchResult } from "@/lib/api";

export function DashboardHeaderActions() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();
  const { showToast } = useToast();

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsSearchOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (trimmedQuery.length < 2) {
      setResults([]);
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      setIsSearching(true);

      try {
        const searchResults = await searchStocks(trimmedQuery);
        setResults(searchResults.slice(0, 5));
        setIsSearchOpen(true);
      } catch {
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => window.clearTimeout(timeoutId);
  }, [query]);

  async function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      return;
    }

    setIsSearching(true);

    try {
      const searchResults = await searchStocks(trimmedQuery);
      setResults(searchResults.slice(0, 5));
      setIsSearchOpen(true);

      if (searchResults.length === 1) {
        router.push(`/stocks/${searchResults[0].ticker}`);
      } else if (searchResults.length === 0) {
        showToast({ message: `No stock found for ${trimmedQuery}` });
      }
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to search" });
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <div ref={containerRef} className="relative flex items-center gap-2">
      <form className="relative hidden md:block" onSubmit={handleSearchSubmit}>
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <Input
          aria-label="Global stock search"
          autoComplete="off"
          className="h-10 w-72 pl-9"
          maxLength={80}
          onChange={(event) => {
            setQuery(event.target.value);
            setIsSearchOpen(true);
          }}
          onFocus={() => setIsSearchOpen(true)}
          placeholder="Search company or ticker"
          value={query}
        />
      </form>

      {isSearchOpen && query.trim().length >= 2 ? (
        <div className="absolute right-0 top-12 z-50 w-[min(32rem,calc(100vw-2rem))] overflow-hidden rounded-md border bg-card shadow-xl">
          <div className="border-b px-4 py-3">
            <p className="text-sm font-semibold">Search Results</p>
            <p className="text-xs text-muted-foreground">Open the stock detail page or its news.</p>
          </div>
          {isSearching ? (
            <p className="px-4 py-5 text-sm text-muted-foreground">Searching...</p>
          ) : results.length === 0 ? (
            <p className="px-4 py-5 text-sm text-muted-foreground">No matches yet.</p>
          ) : (
            <div className="max-h-96 overflow-y-auto">
              {results.map((stock) => (
                <div key={stock.ticker} className="border-b p-4 last:border-b-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        className="inline-flex items-center gap-2 font-semibold text-primary hover:underline"
                        href={`/stocks/${stock.ticker}`}
                        onClick={() => setIsSearchOpen(false)}
                      >
                        <TrendingUp className="h-4 w-4" aria-hidden="true" />
                        {stock.ticker}
                      </Link>
                      <p className="mt-1 truncate text-sm text-muted-foreground">{stock.company_name ?? "Company unavailable"}</p>
                    </div>
                    <p className="shrink-0 text-sm font-medium">
                      {stock.current_price ? `$${stock.current_price.toFixed(2)}` : "N/A"}
                    </p>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/stocks/${stock.ticker}`} onClick={() => setIsSearchOpen(false)}>
                        <ExternalLink className="h-4 w-4" aria-hidden="true" />
                        Detail
                      </Link>
                    </Button>
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/news?ticker=${encodeURIComponent(stock.ticker)}`} onClick={() => setIsSearchOpen(false)}>
                        <Newspaper className="h-4 w-4" aria-hidden="true" />
                        News
                      </Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

    </div>
  );
}
