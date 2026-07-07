from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.predictor import build_prediction_context, get_stock_prediction
from app.schemas.stock import StockPredictionResponse


async def get_prediction(session: AsyncSession, ticker: str) -> StockPredictionResponse:
    return await get_stock_prediction(session, ticker)


async def get_prediction_explanation_context(session: AsyncSession, ticker: str) -> str:
    return await build_prediction_context(session, ticker)
