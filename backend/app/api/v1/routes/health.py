from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.health import DatabaseHealthResponse, HealthResponse
from app.services.health_service import check_database

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def api_health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="api")


@router.get("/db", response_model=DatabaseHealthResponse)
async def database_health_check(
    session: AsyncSession = Depends(get_db_session),
) -> DatabaseHealthResponse:
    database_status = await check_database(session)
    return DatabaseHealthResponse(status="ok", database=database_status)
