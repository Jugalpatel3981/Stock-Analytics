from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.analytics import StockComparison, StockInsights
from app.schemas.stock import (
    StockDetail,
    StockHistoryResponse,
    StockNewsResponse,
    StockSearchResult,
)
from app.services import analytics_service, insights_service, stock_service

router = APIRouter()


@router.get("/search", response_model=list[StockSearchResult])
async def search_stocks(
    query: str = Query(min_length=1, max_length=64),
    _: User = Depends(get_current_user),
) -> list[StockSearchResult]:
    return await stock_service.search_stocks(query)


@router.get("/news", response_model=StockNewsResponse)
async def read_stock_news(
    ticker: str = Query(min_length=1, max_length=12),
    limit: int = Query(default=10, ge=1, le=20),
    _: User = Depends(get_current_user),
) -> StockNewsResponse:
    return await stock_service.get_stock_news(ticker, limit)


@router.get("/compare", response_model=StockComparison)
async def compare_stocks(
    symbols: str = Query(min_length=1, max_length=80, description="Comma-separated tickers"),
    range: Literal["6mo", "1y", "5y"] = Query(default="1y"),
    _: User = Depends(get_current_user),
) -> StockComparison:
    return await analytics_service.compare_stocks(
        analytics_service.normalize_compare_symbols(symbols), range
    )


@router.get("/{ticker}", response_model=StockDetail)
async def read_stock_detail(
    ticker: str,
    _: User = Depends(get_current_user),
) -> StockDetail:
    return await stock_service.get_stock_detail(ticker)


@router.get("/{ticker}/history", response_model=StockHistoryResponse)
async def read_stock_history(
    ticker: str,
    range: Literal["1d", "1wk", "1mo", "1y"] = Query(default="1mo"),
    _: User = Depends(get_current_user),
) -> StockHistoryResponse:
    return await stock_service.get_stock_history(ticker, range)


@router.get("/{ticker}/insights", response_model=StockInsights)
async def read_stock_insights(
    ticker: str,
    _: User = Depends(get_current_user),
) -> StockInsights:
    return await insights_service.get_stock_insights(ticker)
