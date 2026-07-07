import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.market import MarketQuote
from app.services.market_stream_service import get_finnhub_quotes, normalize_symbols, stream_finnhub_trades

router = APIRouter()


@router.get("/quotes", response_model=list[MarketQuote])
async def read_market_quotes(
    symbols: str = Query(min_length=1),
    _: User = Depends(get_current_user),
) -> list[MarketQuote]:
    normalized_symbols = normalize_symbols(symbols)

    if not normalized_symbols:
        return []

    return await get_finnhub_quotes(normalized_symbols)


async def _reject_socket(websocket: WebSocket, message: str) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "error", "message": message})
    await websocket.close(code=1008)


async def _has_valid_access_token(websocket: WebSocket) -> bool:
    settings = get_settings()
    token = websocket.cookies.get(settings.auth_cookie_name)

    if token is None:
        await _reject_socket(websocket, "Authentication is required for live market streaming.")
        return False

    try:
        decode_access_token(token)
    except jwt.PyJWTError:
        await _reject_socket(websocket, "Invalid or expired authentication token.")
        return False

    return True


@router.websocket("/stream")
async def stream_market_data(websocket: WebSocket, symbols: str) -> None:
    if not await _has_valid_access_token(websocket):
        return

    normalized_symbols = normalize_symbols(symbols)

    if not normalized_symbols:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "At least one symbol is required."})
        await websocket.close()
        return

    try:
        await stream_finnhub_trades(websocket, normalized_symbols)
    except WebSocketDisconnect:
        return
