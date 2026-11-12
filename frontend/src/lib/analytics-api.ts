import { apiRequest } from "@/lib/api";

// Returns, weights, volatility and drawdowns are fractions: 0.12 means 12%.

export type PerformancePoint = {
  date: string;
  portfolio: number;
  benchmark: number | null;
};

export type RiskMetrics = {
  total_return: number | null;
  volatility: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  best_day: number | null;
  worst_day: number | null;
};

export type AllocationSlice = {
  label: string;
  value: number;
  weight: number;
};

export type HoldingPerformance = {
  symbol: string;
  quantity: number;
  cost_basis: number;
  value: number;
  gain: number;
  return_since_purchase: number | null;
  benchmark_return: number | null;
  excess_return: number | null;
  weight: number;
};

export type PurchaseComparison = {
  invested: number;
  portfolio_value: number;
  benchmark_value: number | null;
  portfolio_return: number | null;
  benchmark_return: number | null;
};

export type PortfolioAnalytics = {
  as_of: string | null;
  benchmark_symbol: string;
  risk_free_rate: number;
  window_start: string | null;
  window_end: string | null;
  performance: PerformancePoint[];
  portfolio: RiskMetrics;
  benchmark: RiskMetrics;
  beta: number | null;
  since_purchase: PurchaseComparison | null;
  allocation_by_holding: AllocationSlice[];
  allocation_by_sector: AllocationSlice[];
  holdings: HoldingPerformance[];
  warnings: string[];
  excluded_symbols: string[];
};

export type ComparisonRange = "6mo" | "1y" | "5y";

export type ComparisonStats = {
  symbol: string;
  company_name: string | null;
  current_price: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  total_return: number | null;
  volatility: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
};

export type StockComparison = {
  range: ComparisonRange;
  symbols: string[];
  window_start: string | null;
  window_end: string | null;
  points: Array<Record<string, number | string>>;
  stats: ComparisonStats[];
  correlation: { symbols: string[]; values: Array<Array<number | null>> } | null;
  missing_symbols: string[];
};

export type StockInsights = {
  ticker: string;
  available: boolean;
  analyst_ratings: {
    period: string | null;
    strong_buy: number;
    buy: number;
    hold: number;
    sell: number;
    strong_sell: number;
  } | null;
  next_earnings: {
    date: string;
    eps_estimate: number | null;
    revenue_estimate: number | null;
  } | null;
  key_metrics: {
    week_52_high: number | null;
    week_52_high_date: string | null;
    week_52_low: number | null;
    week_52_low_date: string | null;
    dividend_yield: number | null;
    beta: number | null;
    eps_ttm: number | null;
    net_margin: number | null;
    revenue_growth_yoy: number | null;
  } | null;
  data_source: string;
};

export type HoldingImportResult = {
  imported: number;
  skipped: number;
  errors: Array<{ row: number; message: string }>;
};

export function getPortfolioAnalytics() {
  return apiRequest<PortfolioAnalytics>("/portfolio/analytics");
}

export function compareStocks(symbols: string[], range: ComparisonRange) {
  const params = new URLSearchParams({ symbols: symbols.join(","), range });
  return apiRequest<StockComparison>(`/stocks/compare?${params.toString()}`);
}

export function getStockInsights(ticker: string) {
  return apiRequest<StockInsights>(`/stocks/${encodeURIComponent(ticker)}/insights`);
}

export function importPortfolioHoldings(content: string) {
  return apiRequest<HoldingImportResult>("/portfolio/holdings/import", {
    method: "POST",
    body: { content },
  });
}

/** The address of the CSV download. The browser sends the login cookie with it. */
export const PORTFOLIO_EXPORT_URL = "/api/v1/portfolio/holdings/export";
