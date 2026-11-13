"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { RowsSkeleton } from "@/components/ui/skeleton";
import { getStockNews, getWatchlists, type StockNewsItem } from "@/lib/api";

const FALLBACK_TICKER = "NVDA";
const ARTICLE_LIMIT = 5;

function formatPublishDate(value: string | null) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? null
    : date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

async function loadDashboardNews() {
  let ticker = FALLBACK_TICKER;
  try {
    const watchlists = await getWatchlists();
    ticker = watchlists.flatMap((watchlist) => watchlist.stocks)[0]?.ticker ?? FALLBACK_TICKER;
  } catch {
    // Fall back to the default ticker if watchlists cannot be loaded.
  }

  const news = await getStockNews(ticker, ARTICLE_LIMIT);
  return { ticker, articles: news.articles };
}

export function DashboardNews() {
  const [ticker, setTicker] = useState<string | null>(null);
  const [articles, setArticles] = useState<StockNewsItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    loadDashboardNews()
      .then((result) => {
        if (isActive) {
          setTicker(result.ticker);
          setArticles(result.articles);
        }
      })
      .catch((caughtError: unknown) => {
        if (isActive) {
          setError(caughtError instanceof Error ? caughtError.message : "Unable to load news");
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  return (
    <section className="min-w-0 rounded-lg border bg-card/80">
      <div className="flex items-start justify-between gap-4 border-b p-5">
        <div>
          <h2 className="text-base font-semibold">Latest news</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {ticker ? `Recent headlines for ${ticker}.` : "Recent headlines from your watchlist."}
          </p>
        </div>
        <Button size="sm" variant="ghost" asChild>
          <Link href={ticker ? `/news?ticker=${ticker}` : "/news"}>
            More
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </Button>
      </div>
      <div className="p-5">
        {error ? (
          <p className="text-sm text-muted-foreground">{error}</p>
        ) : articles === null ? (
          <RowsSkeleton rows={5} />
        ) : articles.length === 0 ? (
          <p className="text-sm text-muted-foreground">No recent news for {ticker}.</p>
        ) : (
          <ul className="divide-y">
            {articles.map((article) => (
              <li key={article.url ?? article.headline} className="py-3 first:pt-0 last:pb-0">
                {article.url ? (
                  <a className="text-sm font-medium leading-5 hover:underline" href={article.url} rel="noreferrer" target="_blank">
                    {article.headline}
                  </a>
                ) : (
                  <p className="text-sm font-medium leading-5">{article.headline}</p>
                )}
                <p className="mt-1 text-xs text-muted-foreground">
                  {[article.source, formatPublishDate(article.publish_date)].filter(Boolean).join(" · ")}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
