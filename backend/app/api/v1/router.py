from fastapi import APIRouter

from app.api.v1.routes import auth, health, market_stream, portfolio, stocks, watchlists

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(market_stream.router, prefix="/market", tags=["market"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(watchlists.router, prefix="/watchlists", tags=["watchlists"])
