import { getApiBaseUrl } from "@/lib/env";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export type AuthUser = {
  id: number;
  name: string;
  email: string;
  created_at: string;
};

export type AuthResponse = {
  user: AuthUser;
};

export type StockSearchResult = {
  ticker: string;
  company_name: string | null;
  exchange: string | null;
  currency: string | null;
  current_price: number | null;
};

export type StockDetail = StockSearchResult & {
  volume: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  sector: string | null;
  industry: string | null;
  website: string | null;
  business_summary: string | null;
  data_source: string;
};

export type StockHistoryRange = "1d" | "1wk" | "1mo" | "1y";

export type HistoricalPricePoint = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
};

export type StockHistoryResponse = {
  ticker: string;
  range: StockHistoryRange;
  interval: string;
  prices: HistoricalPricePoint[];
  data_source: string;
};

export type StockNewsItem = {
  headline: string;
  source: string | null;
  publish_date: string | null;
  summary: string | null;
  url: string | null;
};

export type StockNewsResponse = {
  ticker: string;
  articles: StockNewsItem[];
  data_source: string;
};

export type MarketQuoteSnapshot = {
  symbol: string;
  current_price: number;
  change: number | null;
  change_percent: number | null;
  high: number | null;
  low: number | null;
  open: number | null;
  previous_close: number | null;
  volume: number | null;
  regular_price: number | null;
  extended_hours_price: number | null;
  has_extended_hours_activity: boolean;
  extended_hours_status: "ACTIVE" | "WAITING" | "NONE";
  extended_hours_source: string | null;
  market_session: MarketSession;
  next_market_open: string | null;
  market_timezone: string;
  timestamp: string;
  source: string;
};

export type MarketSession = "PRE_MARKET" | "OPEN" | "AFTER_HOURS" | "CLOSED";

export type WatchlistStock = {
  id: number;
  ticker: string;
  added_at: string;
};

export type Watchlist = {
  id: number;
  name: string;
  created_at: string;
  stocks: WatchlistStock[];
};

export type PortfolioHolding = {
  id: number;
  symbol: string;
  quantity: number;
  buy_price: number;
  buy_date: string;
  current_price: number | null;
  current_value: number | null;
  cost_basis: number;
  gain_loss: number | null;
  percentage_return: number | null;
  created_at: string;
};

export type PortfolioSummary = {
  total_value: number;
  total_cost: number;
  total_gain_loss: number;
  total_percentage_return: number;
  unpriced_holdings: number;
  holdings: PortfolioHolding[];
};

export type PortfolioGrowthPoint = {
  date: string;
  value: number;
};

export type PortfolioGrowthResponse = {
  points: PortfolioGrowthPoint[];
};

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message = payload?.detail ?? "Request failed";
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function registerUser(input: { name: string; email: string; password: string }) {
  return apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    body: input,
  });
}

export function loginUser(input: { email: string; password: string }) {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: input,
  });
}

export function getMarketStreamToken() {
  return apiRequest<{ token: string; expires_in: number }>("/market/stream-token");
}

export function demoLogin() {
  return apiRequest<AuthResponse>("/auth/demo", {
    method: "POST",
  });
}

export function logoutUser() {
  return apiRequest<{ message: string }>("/auth/logout", {
    method: "POST",
  });
}

export function searchStocks(query: string) {
  const params = new URLSearchParams({ query });
  return apiRequest<StockSearchResult[]>(`/stocks/search?${params.toString()}`);
}

export function getStockHistory(ticker: string, range: StockHistoryRange) {
  const params = new URLSearchParams({ range });
  return apiRequest<StockHistoryResponse>(`/stocks/${ticker}/history?${params.toString()}`);
}

export function getStockNews(ticker: string, limit = 10) {
  const params = new URLSearchParams({ ticker, limit: String(limit) });
  return apiRequest<StockNewsResponse>(`/stocks/news?${params.toString()}`);
}

export function getMarketQuotes(symbols: string[]) {
  const params = new URLSearchParams({ symbols: symbols.join(",") });
  return apiRequest<MarketQuoteSnapshot[]>(`/market/quotes?${params.toString()}`);
}

export function createWatchlist(input: { name: string }) {
  return apiRequest<Watchlist>("/watchlists", {
    method: "POST",
    body: input,
  });
}

export function getWatchlists() {
  return apiRequest<Watchlist[]>("/watchlists");
}

export function addStockToWatchlist(watchlistId: number, input: { ticker: string }) {
  return apiRequest<Watchlist>(`/watchlists/${watchlistId}/stocks`, {
    method: "POST",
    body: input,
  });
}

export function removeStockFromWatchlist(watchlistId: number, ticker: string) {
  return apiRequest<Watchlist>(`/watchlists/${watchlistId}/stocks/${ticker}`, {
    method: "DELETE",
  });
}

export function getPortfolioSummary() {
  return apiRequest<PortfolioSummary>("/portfolio/holdings");
}

export function getPortfolioGrowth() {
  return apiRequest<PortfolioGrowthResponse>("/portfolio/growth");
}

export function createPortfolioHolding(input: {
  symbol: string;
  quantity: number;
  buy_price: number;
  buy_date: string;
}) {
  return apiRequest<PortfolioHolding>("/portfolio/holdings", {
    method: "POST",
    body: input,
  });
}

export function deletePortfolioHolding(holdingId: number) {
  return apiRequest<void>(`/portfolio/holdings/${holdingId}`, {
    method: "DELETE",
  });
}
