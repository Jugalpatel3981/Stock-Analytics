from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.chat import (
    ChatExchangeResponse,
    ChatMessageCreate,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionRead,
)
from app.services import chat_service

router = APIRouter()


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatSessionRead]:
    return await chat_service.list_sessions(session, current_user.id)


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_create: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionRead:
    return await chat_service.create_session(session, current_user.id, session_create)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def read_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionDetail:
    return await chat_service.get_session_detail(session, current_user.id, session_id)


@router.post("/sessions/{session_id}/messages", response_model=ChatExchangeResponse)
async def create_chat_message(
    session_id: int,
    message_create: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatExchangeResponse:
    return await chat_service.create_message_exchange(
        session,
        current_user.id,
        session_id,
        message_create,
    )
