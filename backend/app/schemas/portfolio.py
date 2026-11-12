from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


def _reject_future_date(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise ValueError("Buy date cannot be in the future")

    return value


class PortfolioHoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    buy_date: date

    _buy_date_not_in_future = field_validator("buy_date")(_reject_future_date)


class PortfolioHoldingUpdate(BaseModel):
    """Fields left out keep their current value."""

    quantity: float | None = Field(default=None, gt=0)
    buy_price: float | None = Field(default=None, gt=0)
    buy_date: date | None = None

    _buy_date_not_in_future = field_validator("buy_date")(_reject_future_date)


class PortfolioHoldingImport(BaseModel):
    # The text of a CSV file with symbol, quantity, buy_price and buy_date columns.
    content: str = Field(min_length=1, max_length=200_000)


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
    unpriced_holdings: int = 0
    holdings: list[PortfolioHoldingRead]


class PortfolioGrowthPoint(BaseModel):
    date: str
    value: float


class PortfolioGrowthResponse(BaseModel):
    points: list[PortfolioGrowthPoint]
