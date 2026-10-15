import asyncio
from collections import defaultdict
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import PortfolioHolding
from app.schemas.portfolio import (
    PortfolioGrowthPoint,
    PortfolioGrowthResponse,
    PortfolioHoldingCreate,
    PortfolioHoldingRead,
    PortfolioSummary,
)
from app.services import market_stream_service, stock_service


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def build_holding_read(
    holding: PortfolioHolding, current_price: float | None
) -> PortfolioHoldingRead:
    cost_basis = holding.quantity * holding.buy_price
    current_value = holding.quantity * current_price if current_price is not None else None
    gain_loss = current_value - cost_basis if current_value is not None else None
    percentage_return = (
        (gain_loss / cost_basis) * 100 if gain_loss is not None and cost_basis > 0 else None
    )

    return PortfolioHoldingRead(
        id=holding.id,
        symbol=holding.symbol,
        quantity=holding.quantity,
        buy_price=holding.buy_price,
        buy_date=holding.buy_date,
        current_price=current_price,
        current_value=current_value,
        cost_basis=cost_basis,
        gain_loss=gain_loss,
        percentage_return=percentage_return,
        created_at=holding.created_at,
    )


async def list_raw_holdings(session: AsyncSession, user_id: int) -> list[PortfolioHolding]:
    result = await session.execute(
        select(PortfolioHolding)
        .where(PortfolioHolding.user_id == user_id)
        .order_by(PortfolioHolding.created_at.desc())
    )
    return list(result.scalars().all())


async def get_current_price(symbol: str) -> float | None:
    """Latest price from Finnhub when configured (reliable from cloud hosts), else Yahoo."""
    try:
        quotes = await market_stream_service.get_finnhub_quotes([symbol])
        if quotes and quotes[0].current_price:
            return quotes[0].current_price
    except Exception:  # missing key or Finnhub outage: fall back to Yahoo
        pass

    try:
        detail = await stock_service.get_stock_detail(symbol)
    except HTTPException:
        return None

    return detail.current_price


async def get_portfolio_summary(session: AsyncSession, user_id: int) -> PortfolioSummary:
    holdings = await list_raw_holdings(session, user_id)
    enriched_holdings: list[PortfolioHoldingRead] = []

    # Look up each symbol once, all at the same time.
    symbols = sorted({holding.symbol for holding in holdings})
    prices = dict(zip(symbols, await asyncio.gather(*map(get_current_price, symbols)), strict=True))
    for holding in holdings:
        enriched_holdings.append(build_holding_read(holding, prices[holding.symbol]))

    # Totals cover holdings with a known price, so a provider outage does not look like a loss.
    priced_holdings = [
        holding for holding in enriched_holdings if holding.current_value is not None
    ]
    total_cost = sum(holding.cost_basis for holding in priced_holdings)
    total_value = sum(holding.current_value or 0 for holding in priced_holdings)
    total_gain_loss = total_value - total_cost
    total_percentage_return = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0

    return PortfolioSummary(
        total_value=total_value,
        total_cost=total_cost,
        total_gain_loss=total_gain_loss,
        total_percentage_return=total_percentage_return,
        unpriced_holdings=len(enriched_holdings) - len(priced_holdings),
        holdings=enriched_holdings,
    )


async def create_holding(
    session: AsyncSession,
    user_id: int,
    holding_create: PortfolioHoldingCreate,
) -> PortfolioHoldingRead:
    holding = PortfolioHolding(
        user_id=user_id,
        symbol=normalize_symbol(holding_create.symbol),
        quantity=holding_create.quantity,
        buy_price=holding_create.buy_price,
        buy_date=holding_create.buy_date,
    )
    session.add(holding)
    await session.commit()
    await session.refresh(holding)

    current_price = await get_current_price(holding.symbol)
    return build_holding_read(holding, current_price)


async def delete_holding(session: AsyncSession, user_id: int, holding_id: int) -> None:
    result = await session.execute(
        select(PortfolioHolding).where(
            PortfolioHolding.id == holding_id,
            PortfolioHolding.user_id == user_id,
        )
    )
    holding = result.scalar_one_or_none()

    if holding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio holding not found",
        )

    await session.delete(holding)
    await session.commit()


async def get_portfolio_growth(session: AsyncSession, user_id: int) -> PortfolioGrowthResponse:
    holdings = await list_raw_holdings(session, user_id)
    values_by_date: dict[str, float] = defaultdict(float)

    async def load_history(symbol: str):
        try:
            return await stock_service.get_stock_history(symbol, "1y")
        except HTTPException:
            return None

    symbols = sorted({holding.symbol for holding in holdings})
    histories = dict(zip(symbols, await asyncio.gather(*map(load_history, symbols)), strict=True))

    for holding in holdings:
        history = histories[holding.symbol]
        if history is None:
            continue

        for point in history.prices:
            point_date = point.timestamp[:10]
            if date.fromisoformat(point_date) >= holding.buy_date:
                values_by_date[point_date] += point.close * holding.quantity

    points = [
        PortfolioGrowthPoint(date=point_date, value=round(value, 2))
        for point_date, value in sorted(values_by_date.items())
    ]

    return PortfolioGrowthResponse(points=points)
