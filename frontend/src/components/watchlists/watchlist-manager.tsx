"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useState } from "react";
import { Check, Pencil, Plus, Search, Trash2, X } from "lucide-react";

import { LiveBadge } from "@/components/market/live-badge";
import { MarketStreamErrorToast } from "@/components/market/market-stream-error-toast";
import { LivePrice } from "@/components/market/live-price";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast-provider";
import {
  addStockToWatchlist,
  createWatchlist,
  deleteWatchlist,
  removeStockFromWatchlist,
  renameWatchlist,
  searchStocks,
  type Watchlist,
  type StockSearchResult,
  type WatchlistStock,
} from "@/lib/api";
import { useMarketStream } from "@/lib/market-stream";

type WatchlistManagerProps = {
  initialWatchlists: Watchlist[];
};

export function WatchlistManager({ initialWatchlists }: WatchlistManagerProps) {
  const [watchlists, setWatchlists] = useState(initialWatchlists);
  const { showToast } = useToast();
  const [isCreating, setIsCreating] = useState(false);
  const [activeMutation, setActiveMutation] = useState<string | null>(null);
  const [searchResultsByWatchlist, setSearchResultsByWatchlist] = useState<Record<number, StockSearchResult[]>>({});
  const [searchingWatchlistId, setSearchingWatchlistId] = useState<number | null>(null);
  const [renamingWatchlistId, setRenamingWatchlistId] = useState<number | null>(null);
  const [noResultsByWatchlist, setNoResultsByWatchlist] = useState<Record<number, string | null>>({});
  const trackedSymbols = Array.from(new Set(watchlists.flatMap((watchlist) => watchlist.stocks.map((stock) => stock.ticker))));
  const { quotes, status, error: streamError, lastUpdated, marketSession, nextMarketOpen, hasExtendedHoursActivity } = useMarketStream(trackedSymbols);

  async function handleCreateWatchlist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);

    const form = event.currentTarget;
    const formData = new FormData(form);
    const name = String(formData.get("name") ?? "").trim();

    try {
      const createdWatchlist = await createWatchlist({ name });
      setWatchlists((current) => [createdWatchlist, ...current]);
      form.reset();
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to create watchlist" });
    } finally {
      setIsCreating(false);
    }
  }

  async function handleRenameWatchlist(event: FormEvent<HTMLFormElement>, watchlistId: number) {
    event.preventDefault();
    const name = String(new FormData(event.currentTarget).get("name") ?? "").trim();
    if (!name) {
      return;
    }

    setActiveMutation(`rename-${watchlistId}`);

    try {
      const updatedWatchlist = await renameWatchlist(watchlistId, { name });
      setWatchlists((current) =>
        current.map((watchlist) => (watchlist.id === watchlistId ? updatedWatchlist : watchlist)),
      );
      setRenamingWatchlistId(null);
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to rename watchlist" });
    } finally {
      setActiveMutation(null);
    }
  }

  async function handleDeleteWatchlist(watchlist: Watchlist) {
    const stockCount = watchlist.stocks.length;
    const detail = stockCount > 0 ? ` and the ${stockCount} ${stockCount === 1 ? "stock" : "stocks"} in it` : "";
    if (!window.confirm(`Delete the watchlist "${watchlist.name}"${detail}? This cannot be undone.`)) {
      return;
    }

    setActiveMutation(`delete-${watchlist.id}`);

    try {
      await deleteWatchlist(watchlist.id);
      setWatchlists((current) => current.filter((item) => item.id !== watchlist.id));
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to delete watchlist" });
    } finally {
      setActiveMutation(null);
    }
  }

  async function addTickerToWatchlist(watchlistId: number, ticker: string) {
    const normalizedTicker = ticker.trim().toUpperCase();
    if (!normalizedTicker) {
      return;
    }

    const targetWatchlist = watchlists.find((watchlist) => watchlist.id === watchlistId);
    if (targetWatchlist?.stocks.some((stock) => stock.ticker === normalizedTicker)) {
      showToast({ message: `${normalizedTicker} is already in this watchlist` });
      return;
    }
    setActiveMutation(`add-${watchlistId}`);
    const previousWatchlists = watchlists;
    const optimisticStock: WatchlistStock = {
      id: -Date.now(),
      ticker: normalizedTicker,
      added_at: new Date().toISOString(),
    };

    setWatchlists((current) =>
      current.map((watchlist) =>
        watchlist.id === watchlistId
          ? {
              ...watchlist,
              stocks: [...watchlist.stocks, optimisticStock],
            }
          : watchlist,
      ),
    );
    setSearchResultsByWatchlist((current) => ({ ...current, [watchlistId]: [] }));

    try {
      const updatedWatchlist = await addStockToWatchlist(watchlistId, { ticker: normalizedTicker });
      setWatchlists((current) =>
        current.map((watchlist) => (watchlist.id === watchlistId ? updatedWatchlist : watchlist)),
      );
    } catch (caughtError) {
      setWatchlists(previousWatchlists);
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to add stock" });
    } finally {
      setActiveMutation(null);
    }
  }

  async function handleSearchStocks(event: FormEvent<HTMLFormElement>, watchlistId: number) {
    event.preventDefault();
    setSearchingWatchlistId(watchlistId);

    const formData = new FormData(event.currentTarget);
    const query = String(formData.get("ticker") ?? "").trim();

    if (!query) {
      setSearchingWatchlistId(null);
      return;
    }

    try {
      const results = await searchStocks(query);
      setSearchResultsByWatchlist((current) => ({ ...current, [watchlistId]: results }));
      setNoResultsByWatchlist((current) => ({ ...current, [watchlistId]: results.length === 0 ? query : null }));
    } catch (caughtError) {
      setSearchResultsByWatchlist((current) => ({ ...current, [watchlistId]: [] }));
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to search stocks" });
    } finally {
      setSearchingWatchlistId(null);
    }
  }
  async function handleRemoveStock(watchlistId: number, ticker: string) {
    setActiveMutation(`remove-${watchlistId}-${ticker}`);

    const previousWatchlists = watchlists;
    setWatchlists((current) =>
      current.map((watchlist) =>
        watchlist.id === watchlistId
          ? {
              ...watchlist,
              stocks: watchlist.stocks.filter((stock) => stock.ticker !== ticker),
            }
          : watchlist,
      ),
    );

    try {
      const updatedWatchlist = await removeStockFromWatchlist(watchlistId, ticker);
      setWatchlists((current) =>
        current.map((watchlist) => (watchlist.id === watchlistId ? updatedWatchlist : watchlist)),
      );
    } catch (caughtError) {
      setWatchlists(previousWatchlists);
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to remove stock" });
    } finally {
      setActiveMutation(null);
    }
  }
  return (
    <div className="space-y-5">
      <section className="rounded-lg border bg-card/80 p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-base font-semibold">Create Watchlist</h2>
            <p className="mt-1 text-sm text-muted-foreground">Group the stocks you want to follow.</p>
          </div>
          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleCreateWatchlist}>
            <Input name="name" placeholder="Growth Stocks" minLength={1} maxLength={120} required />
            <Button type="submit" disabled={isCreating}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {isCreating ? "Creating..." : "Create"}
            </Button>
          </form>
        </div>
      </section>

      {watchlists.length === 0 ? (
        <section className="rounded-lg border bg-card/80 p-8 text-center">
          <h2 className="text-lg font-semibold">No watchlists yet</h2>
          <p className="mt-2 text-sm text-muted-foreground">Create your first watchlist, then add tickers like NVDA, AAPL, or MSFT.</p>
        </section>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          {watchlists.map((watchlist) => (
            <section key={watchlist.id} className="rounded-lg border bg-card/80">
              <div className="border-b p-5">
                <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
                  <div className="min-w-[14rem] flex-1">
                    {renamingWatchlistId === watchlist.id ? (
                      <form className="flex items-center gap-2" onSubmit={(event) => handleRenameWatchlist(event, watchlist.id)}>
                        <Input
                          aria-label="Watchlist name"
                          autoFocus
                          className="h-9"
                          defaultValue={watchlist.name}
                          maxLength={120}
                          name="name"
                          required
                        />
                        <Button type="submit" size="sm" disabled={activeMutation === `rename-${watchlist.id}`} aria-label="Save name">
                          <Check className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button type="button" size="sm" variant="ghost" onClick={() => setRenamingWatchlistId(null)} aria-label="Cancel rename">
                          <X className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </form>
                    ) : (
                      <div className="flex items-center gap-1">
                        <h2 className="truncate text-base font-semibold">{watchlist.name}</h2>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => setRenamingWatchlistId(watchlist.id)}
                          aria-label={`Rename ${watchlist.name}`}
                          title="Rename watchlist"
                        >
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteWatchlist(watchlist)}
                          disabled={activeMutation === `delete-${watchlist.id}`}
                          aria-label={`Delete ${watchlist.name}`}
                          title="Delete watchlist"
                        >
                          <Trash2 className="h-4 w-4 text-red-400" aria-hidden="true" />
                        </Button>
                      </div>
                    )}
                    <p className="mt-1 text-sm text-muted-foreground">
                      {watchlist.stocks.length} {watchlist.stocks.length === 1 ? "stock" : "stocks"} tracked
                    </p>
                  </div>
                  <LiveBadge
                    status={status}
                    lastUpdated={lastUpdated}
                    marketSession={marketSession}
                    nextMarketOpen={nextMarketOpen}
                    hasExtendedHoursActivity={hasExtendedHoursActivity}
                  />
                </div>
                <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={(event) => handleSearchStocks(event, watchlist.id)}>
                  <div className="relative flex-1">
                    <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    <Input name="ticker" className="pl-9" placeholder="Search company or ticker, e.g. Nvidia" maxLength={64} required />
                  </div>
                  <Button type="submit" variant="secondary" disabled={searchingWatchlistId === watchlist.id}>
                    <Search className="h-4 w-4" aria-hidden="true" />
                    {searchingWatchlistId === watchlist.id ? "Searching..." : "Search"}
                  </Button>
                </form>

                {searchResultsByWatchlist[watchlist.id]?.length ? (
                  <div className="mt-3 overflow-hidden rounded-md border bg-background/40">
                    {searchResultsByWatchlist[watchlist.id].map((result) => (
                      <div
                        key={result.ticker}
                        className="grid gap-3 border-b px-3 py-3 text-sm last:border-b-0 sm:grid-cols-[0.8fr_1.5fr_auto] sm:items-center"
                      >
                        <div>
                          <p className="font-semibold text-primary">{result.ticker}</p>
                          <p className="text-xs text-muted-foreground">{result.current_price ? `$${result.current_price.toFixed(2)}` : result.currency ?? ""}</p>
                        </div>
                        <p className="text-muted-foreground">{result.company_name ?? "Company unavailable"}</p>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => addTickerToWatchlist(watchlist.id, result.ticker)}
                          disabled={activeMutation === `add-${watchlist.id}`}
                        >
                          <Plus className="h-4 w-4" aria-hidden="true" />
                          Add
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : noResultsByWatchlist[watchlist.id] ? (
                  <p className="mt-3 rounded-md border bg-background/40 px-3 py-3 text-sm text-muted-foreground">
                    No stocks found for &quot;{noResultsByWatchlist[watchlist.id]}&quot;.
                  </p>
                ) : null}
              </div>

              <div className="p-5">
                {watchlist.stocks.length === 0 ? (
                  <p className="rounded-md border bg-background/40 p-4 text-sm text-muted-foreground">No stocks added yet.</p>
                ) : (
                  <div className="space-y-2">
                    {watchlist.stocks.map((stock) => (
                      <div key={stock.id} className="grid gap-3 rounded-md border bg-background/40 px-4 py-3 sm:grid-cols-[1fr_1.5fr_auto] sm:items-center">
                        <div>
                          <Link className="font-semibold text-primary hover:underline" href={`/stocks/${stock.ticker}`}>
                            {stock.ticker}
                          </Link>
                        </div>
                        <LivePrice quote={quotes[stock.ticker]} compact />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveStock(watchlist.id, stock.ticker)}
                          disabled={activeMutation === `remove-${watchlist.id}-${stock.ticker}`}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                          Remove
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
                <MarketStreamErrorToast error={streamError} />
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}



