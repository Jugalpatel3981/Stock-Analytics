"use client";

import { ExternalLink, Newspaper, Search } from "lucide-react";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RowsSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast-provider";
import { getStockNews, type StockNewsItem } from "@/lib/api";

type StockNewsFeedProps = {
  initialTicker: string;
};

function formatPublishDate(value: string | null) {
  if (!value) {
    return "Date unavailable";
  }

  const parsedDate = new Date(value);

  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  return parsedDate.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function StockNewsFeed({ initialTicker }: StockNewsFeedProps) {
  const [ticker, setTicker] = useState(initialTicker);
  const [activeTicker, setActiveTicker] = useState(initialTicker);
  const [articles, setArticles] = useState<StockNewsItem[]>([]);
  const { showToast } = useToast();
  const [isLoading, setIsLoading] = useState(true);

  const loadNews = useCallback(async (nextTicker: string) => {
    setIsLoading(true);

    try {
      const news = await getStockNews(nextTicker.trim().toUpperCase());
      setActiveTicker(news.ticker);
      setArticles(news.articles);
    } catch (caughtError) {
      setArticles([]);
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to load stock news" });
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadNews(initialTicker);
  }, [initialTicker, loadNews]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadNews(ticker);
  }

  return (
    <div className="space-y-5">
      <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleSubmit}>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <Input
            className="pl-9 uppercase"
            maxLength={12}
            onChange={(event) => setTicker(event.target.value)}
            placeholder="Filter by ticker, e.g. AAPL"
            required
            value={ticker}
          />
        </div>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Loading..." : "Filter"}
        </Button>
      </form>

      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{activeTicker} Headlines</p>
          <p className="text-xs text-muted-foreground">News can move prices, but it is not investment advice.</p>
        </div>
        <Badge variant="outline">{articles.length} articles</Badge>
      </div>

      {isLoading ? (
        <div className="rounded-md border bg-background/40 p-4">
          <RowsSkeleton rows={5} />
        </div>
      ) : articles.length === 0 ? (
        <div className="rounded-md border bg-background/40 px-4 py-8 text-center text-sm text-muted-foreground">
          No recent articles found for this ticker.
        </div>
      ) : (
        <div className="grid gap-3">
            {articles.map((article) => (
              <article key={`${article.headline}-${article.publish_date ?? "unknown"}`} className="rounded-lg border bg-background/40 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Newspaper className="h-3.5 w-3.5" aria-hidden="true" />
                        {article.source ?? "Unknown source"}
                      </span>
                      <span>{formatPublishDate(article.publish_date)}</span>
                    </div>
                    <h3 className="text-base font-semibold leading-6">{article.headline}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {article.summary ?? "Summary unavailable from the provider."}
                    </p>
                  </div>
                  {article.url ? (
                    <Button asChild size="sm" variant="outline">
                      <a href={article.url} rel="noreferrer" target="_blank">
                        <ExternalLink className="h-4 w-4" aria-hidden="true" />
                        Open
                      </a>
                    </Button>
                  ) : null}
                </div>
              </article>
            ))}
        </div>
      )}
    </div>
  );
}

