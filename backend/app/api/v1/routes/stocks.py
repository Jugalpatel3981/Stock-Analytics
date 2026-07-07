from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.stock import (
    StockDetail,
    StockHistoryResponse,
    StockNewsResponse,
    StockPredictionResponse,
    StockSearchResult,
)
from app.services import prediction_service, stock_service

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


@router.get("/{ticker}/prediction", response_model=StockPredictionResponse)
async def read_stock_prediction(
    ticker: str,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StockPredictionResponse:
    return await prediction_service.get_prediction(session, ticker)


