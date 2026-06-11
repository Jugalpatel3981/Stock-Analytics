"use client";

import { ExternalLink, Newspaper, Search } from "lucide-react";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { SentimentTrendChart } from "@/components/news/sentiment-trend-chart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStockNews, type StockNewsItem, type StockSentimentTrendPoint } from "@/lib/api";
import { cn } from "@/lib/utils";

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
  const [sentimentTrend, setSentimentTrend] = useState<StockSentimentTrendPoint[]>([]);
  const [sentimentModel, setSentimentModel] = useState("ProsusAI/finbert");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadNews = useCallback(async (nextTicker: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const news = await getStockNews(nextTicker.trim().toUpperCase());
      setActiveTicker(news.ticker);
      setArticles(news.articles);
      setSentimentTrend(news.sentiment_trend);
      setSentimentModel(news.sentiment_model);
    } catch (caughtError) {
      setArticles([]);
      setSentimentTrend([]);
      setError(caughtError instanceof Error ? caughtError.message : "Unable to load stock news");
    } finally {
      setIsLoading(false);
    }
  }, []);

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

      {error ? <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}

      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{activeTicker} Headlines</p>
          <p className="text-xs text-muted-foreground">Sentiment model: {sentimentModel}. News can move prices, but it is not investment advice.</p>
        </div>
        <Badge variant="outline">{articles.length} articles</Badge>
      </div>

      {isLoading ? (
        <div className="rounded-md border bg-background/40 px-4 py-8 text-center text-sm text-muted-foreground">
          Loading financial headlines...
        </div>
      ) : articles.length === 0 ? (
        <div className="rounded-md border bg-background/40 px-4 py-8 text-center text-sm text-muted-foreground">
          No recent articles found for this ticker.
        </div>
      ) : (
        <>
          <section className="rounded-lg border bg-background/40 p-4">
            <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h3 className="text-base font-semibold">Sentiment Trend</h3>
                <p className="text-sm text-muted-foreground">Daily article counts with average sentiment score from -1 to 1.</p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-md border border-emerald-400/30 bg-emerald-400/10 px-2 py-1 text-emerald-300">Positive</span>
                <span className="rounded-md border border-slate-400/30 bg-slate-400/10 px-2 py-1 text-slate-300">Neutral</span>
                <span className="rounded-md border border-red-400/30 bg-red-400/10 px-2 py-1 text-red-300">Negative</span>
              </div>
            </div>
            <SentimentTrendChart points={sentimentTrend} />
          </section>

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
                      <span
                        className={cn(
                          "rounded-md border px-2 py-0.5 font-medium",
                          article.sentiment_label === "Positive" && "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
                          article.sentiment_label === "Neutral" && "border-slate-400/30 bg-slate-400/10 text-slate-300",
                          article.sentiment_label === "Negative" && "border-red-400/30 bg-red-400/10 text-red-300",
                        )}
                      >
                        {article.sentiment_label} {article.sentiment_score.toFixed(2)}
                      </span>
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
        </>
      )}
    </div>
  );
}
