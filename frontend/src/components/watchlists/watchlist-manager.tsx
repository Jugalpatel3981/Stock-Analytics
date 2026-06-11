"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  addStockToWatchlist,
  createWatchlist,
  removeStockFromWatchlist,
  type Watchlist,
} from "@/lib/api";

type WatchlistManagerProps = {
  initialWatchlists: Watchlist[];
};

export function WatchlistManager({ initialWatchlists }: WatchlistManagerProps) {
  const [watchlists, setWatchlists] = useState(initialWatchlists);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [activeMutation, setActiveMutation] = useState<string | null>(null);

  async function handleCreateWatchlist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsCreating(true);

    const form = event.currentTarget;
    const formData = new FormData(form);
    const name = String(formData.get("name") ?? "").trim();

    try {
      const createdWatchlist = await createWatchlist({ name });
      setWatchlists((current) => [createdWatchlist, ...current]);
      form.reset();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to create watchlist");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleAddStock(event: FormEvent<HTMLFormElement>, watchlistId: number) {
    event.preventDefault();
    setError(null);
    setActiveMutation(`add-${watchlistId}`);

    const form = event.currentTarget;
    const formData = new FormData(form);
    const ticker = String(formData.get("ticker") ?? "").trim().toUpperCase();

    try {
      const updatedWatchlist = await addStockToWatchlist(watchlistId, { ticker });
      setWatchlists((current) =>
        current.map((watchlist) => (watchlist.id === watchlistId ? updatedWatchlist : watchlist)),
      );
      form.reset();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to add stock");
    } finally {
      setActiveMutation(null);
    }
  }

  async function handleRemoveStock(watchlistId: number, ticker: string) {
    setError(null);
    setActiveMutation(`remove-${watchlistId}-${ticker}`);

    try {
      const updatedWatchlist = await removeStockFromWatchlist(watchlistId, ticker);
      setWatchlists((current) =>
        current.map((watchlist) => (watchlist.id === watchlistId ? updatedWatchlist : watchlist)),
      );
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to remove stock");
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
            <p className="mt-1 text-sm text-muted-foreground">Group tickers for research, monitoring, and future alerts.</p>
          </div>
          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleCreateWatchlist}>
            <Input name="name" placeholder="Growth Stocks" minLength={1} maxLength={120} required />
            <Button type="submit" disabled={isCreating}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {isCreating ? "Creating..." : "Create"}
            </Button>
          </form>
        </div>
        {error ? <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}
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
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold">{watchlist.name}</h2>
                    <p className="mt-1 text-sm text-muted-foreground">{watchlist.stocks.length} stocks tracked</p>
                  </div>
                  <Badge variant="secondary">Watchlist</Badge>
                </div>
                <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={(event) => handleAddStock(event, watchlist.id)}>
                  <Input className="uppercase" name="ticker" placeholder="Ticker, e.g. NVDA" maxLength={12} required />
                  <Button type="submit" variant="secondary" disabled={activeMutation === `add-${watchlist.id}`}>
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    Add
                  </Button>
                </form>
              </div>

              <div className="p-5">
                {watchlist.stocks.length === 0 ? (
                  <p className="rounded-md border bg-background/40 p-4 text-sm text-muted-foreground">No stocks added yet.</p>
                ) : (
                  <div className="space-y-2">
                    {watchlist.stocks.map((stock) => (
                      <div key={stock.id} className="flex items-center justify-between gap-3 rounded-md border bg-background/40 px-4 py-3">
                        <Link className="font-semibold text-primary hover:underline" href={`/stocks/${stock.ticker}`}>
                          {stock.ticker}
                        </Link>
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
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
