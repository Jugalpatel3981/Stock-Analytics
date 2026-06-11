from datetime import date, datetime

from pydantic import BaseModel, Field


class PortfolioHoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    buy_date: date


class PortfolioHoldingRead(BaseModel):
    id: int
    symbol: str
    quantity: float
    buy_price: float
    buy_date: date
    current_price: float | None = None
    current_value: float | None = None
    cost_basis: float
    gain_loss: float | None = None
    percentage_return: float | None = None
    created_at: datetime


class PortfolioSummary(BaseModel):
    total_value: float
    total_cost: float
    total_gain_loss: float
    total_percentage_return: float
    holdings: list[PortfolioHoldingRead]


class PortfolioGrowthPoint(BaseModel):
    date: str
    value: float


class PortfolioGrowthResponse(BaseModel):
    points: list[PortfolioGrowthPoint]
