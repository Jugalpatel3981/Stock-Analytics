from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.analytics import HoldingImportResult, PortfolioAnalytics
from app.schemas.portfolio import (
    PortfolioGrowthResponse,
    PortfolioHoldingCreate,
    PortfolioHoldingImport,
    PortfolioHoldingRead,
    PortfolioHoldingUpdate,
    PortfolioSummary,
)
from app.services import analytics_service, portfolio_service

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


@router.get("/holdings/export")
async def export_holdings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    csv_content = await portfolio_service.export_holdings_csv(session, current_user.id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="portfolio-holdings.csv"'},
    )


@router.post("/holdings/import", response_model=HoldingImportResult)
async def import_holdings(
    holding_import: PortfolioHoldingImport,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> HoldingImportResult:
    return await portfolio_service.import_holdings_csv(
        session, current_user.id, holding_import.content
    )


@router.patch("/holdings/{holding_id}", response_model=PortfolioHoldingRead)
async def update_holding(
    holding_id: int,
    holding_update: PortfolioHoldingUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PortfolioHoldingRead:
    return await portfolio_service.update_holding(
        session, current_user.id, holding_id, holding_update
    )


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


@router.get("/analytics", response_model=PortfolioAnalytics)
async def read_portfolio_analytics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PortfolioAnalytics:
    return await analytics_service.get_portfolio_analytics(session, current_user.id)
