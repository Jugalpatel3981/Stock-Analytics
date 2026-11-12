from datetime import datetime

from pydantic import BaseModel, Field


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WatchlistUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WatchlistStockCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)


class WatchlistStockRead(BaseModel):
    id: int
    ticker: str
    added_at: datetime


class WatchlistRead(BaseModel):
    id: int
    name: str
    created_at: datetime
    stocks: list[WatchlistStockRead] = []
