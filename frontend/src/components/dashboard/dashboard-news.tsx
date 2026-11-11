"use client";

import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { getStockNews, getWatchlists, type StockNewsItem } from "@/lib/api";

const FALLBACK_TICKER = "NVDA";
const ARTICLE_LIMIT = 4;

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

  if (error) {
    return <p className="rounded-md border bg-background/40 p-4 text-sm text-muted-foreground">{error}</p>;
  }

  if (articles === null) {
    return <p className="rounded-md border bg-background/40 p-4 text-sm text-muted-foreground">Loading latest news...</p>;
  }

  if (articles.length === 0) {
    return <p className="rounded-md border bg-background/40 p-4 text-sm text-muted-foreground">No recent news for {ticker}.</p>;
  }

  return (
    <div className="space-y-3">
      {articles.map((article) => (
        <article key={article.url ?? article.headline} className="rounded-md border bg-background/40 p-4">
          <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
            <span>
              {ticker} · {article.source ?? "News"}
            </span>
            <span>{formatPublishDate(article.publish_date)}</span>
          </div>
          <h2 className="mt-2 text-sm font-medium leading-5">
            {article.url ? (
              <a className="hover:underline" href={article.url} rel="noreferrer" target="_blank">
                {article.headline}
                <ExternalLink className="ml-1 inline h-3 w-3 text-muted-foreground" aria-hidden="true" />
              </a>
            ) : (
              article.headline
            )}
          </h2>
        </article>
      ))}
      <Link className="block text-center text-xs font-medium text-primary hover:underline" href={`/news?ticker=${ticker}`}>
        More news
      </Link>
    </div>
  );
}
