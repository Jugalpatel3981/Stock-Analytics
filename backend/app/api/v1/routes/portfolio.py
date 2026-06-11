from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioGrowthResponse,
    PortfolioHoldingCreate,
    PortfolioHoldingRead,
    PortfolioSummary,
)
from app.services import portfolio_service

router = APIRouter()


@router.get("/holdings", response_model=PortfolioSummary)
async def list_holdings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PortfolioSummary:
    return await portfolio_service.get_portfolio_summary(session, current_user.id)


@router.post("/holdings", response_model=PortfolioHoldingRead, status_code=status.HTTP_201_CREATED)
async def create_holding(
    holding_create: PortfolioHoldingCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PortfolioHoldingRead:
    return await portfolio_service.create_holding(session, current_user.id, holding_create)


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await portfolio_service.delete_holding(session, current_user.id, holding_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/growth", response_model=PortfolioGrowthResponse)
async def read_portfolio_growth(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PortfolioGrowthResponse:
    return await portfolio_service.get_portfolio_growth(session, current_user.id)
