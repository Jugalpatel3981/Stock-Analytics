from typing import Literal

from pydantic import BaseModel

MarketSession = Literal["PRE_MARKET", "OPEN", "AFTER_HOURS", "CLOSED"]
ExtendedHoursStatus = Literal["ACTIVE", "WAITING", "NONE"]


class MarketQuote(BaseModel):
    symbol: str
    current_price: float
    change: float | None = None
    change_percent: float | None = None
    high: float | None = None
    low: float | None = None
    open: float | None = None
    previous_close: float | None = None
    volume: int | None = None
    regular_price: float | None = None
    extended_hours_price: float | None = None
    has_extended_hours_activity: bool = False
    extended_hours_status: ExtendedHoursStatus = "NONE"
    extended_hours_source: str | None = None
    market_session: MarketSession
    next_market_open: str | None = None
    market_timezone: str = "America/New_York"
    timestamp: str
    source: str = "Finnhub"
