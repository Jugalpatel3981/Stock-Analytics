from pydantic import BaseModel, Field


class StockSearchResult(BaseModel):
    ticker: str
    company_name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    current_price: float | None = None


class StockDetail(BaseModel):
    ticker: str
    company_name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    current_price: float | None = None
    volume: int | None = None
    market_cap: int | None = None
    pe_ratio: float | None = None
    sector: str | None = None
    industry: str | None = None
    website: str | None = None
    business_summary: str | None = Field(default=None, max_length=2500)
    data_source: str = "Yahoo Finance via yfinance"


class HistoricalPricePoint(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None


class StockHistoryResponse(BaseModel):
    ticker: str
    range: str
    interval: str
    prices: list[HistoricalPricePoint]
    data_source: str = "Yahoo Finance via yfinance"


class StockNewsItem(BaseModel):
    headline: str
    source: str | None = None
    publish_date: str | None = None
    summary: str | None = Field(default=None, max_length=1000)
    url: str | None = None
    sentiment_label: str = "Neutral"
    sentiment_score: float = 0.0


class StockSentimentTrendPoint(BaseModel):
    date: str
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    average_score: float = 0.0


class StockNewsResponse(BaseModel):
    ticker: str
    articles: list[StockNewsItem]
    sentiment_trend: list[StockSentimentTrendPoint] = []
    sentiment_model: str = "ProsusAI/finbert"
    data_source: str = "Yahoo Finance via yfinance"


class StockPredictionResponse(BaseModel):
    ticker: str
    predicted_close: float
    latest_close: float
    confidence_score: float
    historical_accuracy: float
    training_rows: int
    feature_summary: list[str]
    model_name: str = "XGBoost Regressor"
    prediction_horizon: str = "Next trading day close"
    data_source: str = "Yahoo Finance via yfinance"
