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
  sentiment_label: "Positive" | "Neutral" | "Negative";
  sentiment_score: number;
};

export type StockSentimentTrendPoint = {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  average_score: number;
};

export type StockNewsResponse = {
  ticker: string;
  articles: StockNewsItem[];
  sentiment_trend: StockSentimentTrendPoint[];
  sentiment_model: string;
  data_source: string;
};

export type PredictionBacktest = {
  test_days: number;
  direction_accuracy: number;
  baseline_direction_accuracy: number;
  mae: number;
  baseline_mae: number;
  skill_score: number;
  strategy_return: number;
  buy_and_hold_return: number;
};

export type StockPrediction = {
  ticker: string;
  status: "ready" | "preparing";
  predicted_close: number | null;
  predicted_return_percent: number | null;
  direction: "up" | "down" | "flat" | null;
  latest_close: number | null;
  expected_price_low: number | null;
  expected_price_high: number | null;
  backtest: PredictionBacktest | null;
  prediction_timestamp: string | null;
  message: string | null;
  prediction_horizon: string;
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

export type ChatRole = "user" | "assistant";

export type ChatSource = {
  id: number | null;
  stock_symbol: string | null;
  source_name: string;
  title: string;
  published_at: string | null;
  url: string | null;
};

export type ChatMessage = {
  id: number;
  role: ChatRole;
  content: string;
  created_at: string;
  stock_symbol: string | null;
  sources: ChatSource[];
};

export type ChatSession = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatSessionDetail = ChatSession & {
  messages: ChatMessage[];
};

export type ChatExchangeResponse = {
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
};

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

export function getStockPrediction(ticker: string) {
  return apiRequest<StockPrediction>(`/stocks/${ticker}/prediction`);
}

export function getMarketQuotes(symbols: string[]) {
  const params = new URLSearchParams({ symbols: symbols.join(",") });
  return apiRequest<MarketQuoteSnapshot[]>(`/market/quotes?${params.toString()}`);
}

export function getChatSessions() {
  return apiRequest<ChatSession[]>("/chat/sessions");
}

export function createChatSession(input: { title?: string | null }) {
  return apiRequest<ChatSession>("/chat/sessions", {
    method: "POST",
    body: input,
  });
}

export function getChatSession(sessionId: number) {
  return apiRequest<ChatSessionDetail>(`/chat/sessions/${sessionId}`);
}

export function deleteChatSession(sessionId: number) {
  return apiRequest<void>(`/chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export function sendChatMessage(sessionId: number, input: { content: string }) {
  return apiRequest<ChatExchangeResponse>(`/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    body: input,
  });
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
