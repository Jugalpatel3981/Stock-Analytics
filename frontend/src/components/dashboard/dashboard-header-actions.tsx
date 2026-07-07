"use client";

import { Bot, ExternalLink, Newspaper, Search, Sparkles, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast-provider";
import { searchStocks, type StockSearchResult } from "@/lib/api";
import { cn } from "@/lib/utils";

const analysisTypes = [
  { value: "overview", label: "Stock Overview" },
  { value: "news", label: "News Summary" },
  { value: "sentiment", label: "Sentiment Analysis" },
  { value: "prediction", label: "Prediction Explanation" },
];

function buildAnalysisPrompt(symbolOrCompany: string, analysisType: string) {
  const target = symbolOrCompany.trim();

  if (analysisType === "news") {
    return `Summarize recent developments for ${target} using stock data, news, sentiment, and sources.`;
  }

  if (analysisType === "sentiment") {
    return `What is the current market sentiment for ${target}? Use recent news, sentiment data, and cite sources.`;
  }

  if (analysisType === "prediction") {
    return `Explain the current prediction signal for ${target}. Use available indicators, price data, and news sentiment. Do not fabricate reasoning.`;
  }

  return `Analyze ${target} today using stock data, recent news, sentiment, risks, and source citations.`;
}

function assistantHref(prompt: string) {
  return `/assistant?prompt=${encodeURIComponent(prompt)}`;
}

export function DashboardHeaderActions() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(false);
  const [analysisTarget, setAnalysisTarget] = useState("");
  const [analysisType, setAnalysisType] = useState("overview");
  const containerRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();
  const { showToast } = useToast();

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsSearchOpen(false);
        setIsAnalysisOpen(false);
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

  const selectedAnalysisLabel = useMemo(
    () => analysisTypes.find((type) => type.value === analysisType)?.label ?? "Stock Overview",
    [analysisType],
  );

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

  function handleStartAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = analysisTarget.trim();

    if (!target) {
      showToast({ message: "Enter a company or ticker to analyze." });
      return;
    }

    router.push(assistantHref(buildAnalysisPrompt(target, analysisType)));
    setIsAnalysisOpen(false);
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
          placeholder="Search symbols, company, news"
          value={query}
        />
      </form>

      <Button type="button" size="sm" onClick={() => setIsAnalysisOpen((current) => !current)}>
        New Analysis
      </Button>

      {isSearchOpen && query.trim().length >= 2 ? (
        <div className="absolute right-0 top-12 z-50 w-[min(32rem,calc(100vw-2rem))] overflow-hidden rounded-md border bg-card shadow-xl">
          <div className="border-b px-4 py-3">
            <p className="text-sm font-semibold">Search Results</p>
            <p className="text-xs text-muted-foreground">Open stocks, news, or start an AI research prompt.</p>
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
                    <Button size="sm" variant="secondary" asChild>
                      <Link
                        href={assistantHref(buildAnalysisPrompt(stock.ticker, "overview"))}
                        onClick={() => setIsSearchOpen(false)}
                      >
                        <Bot className="h-4 w-4" aria-hidden="true" />
                        Ask AI
                      </Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {isAnalysisOpen ? (
        <div className="absolute right-0 top-12 z-50 w-[min(28rem,calc(100vw-2rem))] rounded-md border bg-card p-4 shadow-xl">
          <div className="mb-4">
            <p className="text-sm font-semibold">New Analysis</p>
            <p className="text-xs text-muted-foreground">Create a focused AI assistant prompt with stock, news, and sentiment context.</p>
          </div>
          <form className="space-y-3" onSubmit={handleStartAnalysis}>
            <div>
              <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground" htmlFor="analysis-target">
                Company or ticker
              </label>
              <Input
                id="analysis-target"
                maxLength={80}
                onChange={(event) => setAnalysisTarget(event.target.value)}
                placeholder="e.g. Nvidia or NVDA"
                value={analysisTarget}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground" htmlFor="analysis-type">
                Analysis type
              </label>
              <select
                id="analysis-type"
                className={cn(
                  "h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                )}
                onChange={(event) => setAnalysisType(event.target.value)}
                value={analysisType}
              >
                {analysisTypes.map((type) => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            <Button className="w-full" type="submit">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              Start {selectedAnalysisLabel}
            </Button>
          </form>
        </div>
      ) : null}
    </div>
  );
}
