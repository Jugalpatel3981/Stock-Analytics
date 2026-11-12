from pydantic import BaseModel


class PerformancePoint(BaseModel):
    date: str
    portfolio: float
    benchmark: float | None = None


class RiskMetrics(BaseModel):
    """Figures for one series over the analysis window. Fractions, not percentages."""

    total_return: float | None = None
    volatility: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    best_day: float | None = None
    worst_day: float | None = None


class AllocationSlice(BaseModel):
    label: str
    value: float
    weight: float


class HoldingPerformance(BaseModel):
    symbol: str
    quantity: float
    cost_basis: float
    value: float
    gain: float
    return_since_purchase: float | None = None
    # What the benchmark returned over the same holding period(s).
    benchmark_return: float | None = None
    excess_return: float | None = None
    weight: float


class PurchaseComparison(BaseModel):
    """What the same money, invested on the same dates, would be worth in the benchmark."""

    invested: float
    portfolio_value: float
    benchmark_value: float | None = None
    portfolio_return: float | None = None
    benchmark_return: float | None = None


class PortfolioAnalytics(BaseModel):
    as_of: str | None = None
    benchmark_symbol: str
    risk_free_rate: float
    window_start: str | None = None
    window_end: str | None = None
    performance: list[PerformancePoint] = []
    portfolio: RiskMetrics = RiskMetrics()
    benchmark: RiskMetrics = RiskMetrics()
    beta: float | None = None
    since_purchase: PurchaseComparison | None = None
    allocation_by_holding: list[AllocationSlice] = []
    allocation_by_sector: list[AllocationSlice] = []
    holdings: list[HoldingPerformance] = []
    warnings: list[str] = []
    excluded_symbols: list[str] = []


class ComparisonStats(BaseModel):
    symbol: str
    company_name: str | None = None
    current_price: float | None = None
    market_cap: int | None = None
    pe_ratio: float | None = None
    total_return: float | None = None
    volatility: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None


class CorrelationMatrix(BaseModel):
    symbols: list[str]
    # values[i][j] is the correlation between symbols[i] and symbols[j].
    values: list[list[float | None]]


class StockComparison(BaseModel):
    range: str
    symbols: list[str]
    window_start: str | None = None
    window_end: str | None = None
    # One row per trading day: {"date": "2026-01-02", "AAPL": 100.0, "MSFT": 100.0}
    points: list[dict[str, float | str]] = []
    stats: list[ComparisonStats] = []
    correlation: CorrelationMatrix | None = None
    missing_symbols: list[str] = []


class AnalystRatings(BaseModel):
    period: str | None = None
    strong_buy: int = 0
    buy: int = 0
    hold: int = 0
    sell: int = 0
    strong_sell: int = 0


class NextEarnings(BaseModel):
    date: str
    eps_estimate: float | None = None
    revenue_estimate: float | None = None


class KeyMetrics(BaseModel):
    week_52_high: float | None = None
    week_52_high_date: str | None = None
    week_52_low: float | None = None
    week_52_low_date: str | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    eps_ttm: float | None = None
    net_margin: float | None = None
    revenue_growth_yoy: float | None = None


class StockInsights(BaseModel):
    ticker: str
    available: bool = True
    analyst_ratings: AnalystRatings | None = None
    next_earnings: NextEarnings | None = None
    key_metrics: KeyMetrics | None = None
    data_source: str = "Finnhub"


class HoldingImportError(BaseModel):
    row: int
    message: str


class HoldingImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[HoldingImportError] = []
