from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ChatRole = Literal["user", "assistant"]


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=160)


class ChatMessageRead(BaseModel):
    id: int
    role: ChatRole
    content: str
    created_at: datetime
    stock_symbol: str | None = None
    confidence_score: int | None = None
    sources: list["ChatSourceRead"] = Field(default_factory=list)


class ChatSourceRead(BaseModel):
    id: int | None = None
    stock_symbol: str | None = None
    source_name: str
    title: str
    published_at: str | None = None
    url: str | None = None


class ChatSessionRead(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionRead):
    messages: list[ChatMessageRead]


class ChatExchangeResponse(BaseModel):
    session: ChatSessionRead
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead


ChatMessageRead.model_rebuild()
