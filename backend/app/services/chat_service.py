import re
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import (
    ChatExchangeResponse,
    ChatMessageCreate,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionRead,
)
from app.services import openai_service, stock_service

COMPANY_TICKERS = {
    "apple": "AAPL",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "meta": "META",
    "google": "GOOGL",
    "alphabet": "GOOGL",
}


def _session_to_read(session: ChatSession) -> ChatSessionRead:
    return ChatSessionRead(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _message_to_read(message: ChatMessage) -> ChatMessageRead:
    return ChatMessageRead(
        id=message.id,
        role=message.role,  # type: ignore[arg-type]
        content=message.content,
        created_at=message.created_at,
    )


def _build_title(content: str) -> str:
    title = " ".join(content.strip().split())
    return title[:80] if title else "New AI chat"


def _extract_tickers(content: str) -> list[str]:
    explicit_tickers = set(re.findall(r"\$([A-Za-z]{1,5})\b", content))
    uppercase_tickers = set(re.findall(r"\b[A-Z]{2,5}\b", content))
    tickers = {ticker.upper() for ticker in explicit_tickers | uppercase_tickers}
    lowered_content = content.lower()

    for company_name, ticker in COMPANY_TICKERS.items():
        if company_name in lowered_content:
            tickers.add(ticker)

    ignored_terms = {"AI", "API", "CEO", "ETF", "USD", "PE", "IPO", "GDP", "CPI"}
    return sorted(ticker for ticker in tickers if ticker not in ignored_terms)[:3]


async def list_sessions(session: AsyncSession, user_id: int) -> list[ChatSessionRead]:
    result = await session.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return [_session_to_read(chat_session) for chat_session in result.scalars().all()]


async def create_session(
    session: AsyncSession,
    user_id: int,
    session_create: ChatSessionCreate,
) -> ChatSessionRead:
    chat_session = ChatSession(user_id=user_id, title=session_create.title or "New AI chat")
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)
    return _session_to_read(chat_session)


async def _get_owned_session(
    session: AsyncSession,
    user_id: int,
    session_id: int,
) -> ChatSession:
    result = await session.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    chat_session = result.scalar_one_or_none()

    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    return chat_session


async def get_session_detail(
    session: AsyncSession,
    user_id: int,
    session_id: int,
) -> ChatSessionDetail:
    chat_session = await _get_owned_session(session, user_id, session_id)
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )

    return ChatSessionDetail(
        **_session_to_read(chat_session).model_dump(),
        messages=[_message_to_read(message) for message in result.scalars().all()],
    )


async def _build_market_context(content: str) -> str:
    tickers = _extract_tickers(content)
    context_sections: list[str] = []

    for ticker in tickers:
        try:
            detail = await stock_service.get_stock_detail(ticker)
            context_sections.append(
                "\n".join(
                    [
                        f"Stock: {detail.ticker}",
                        f"Company: {detail.company_name or 'Unavailable'}",
                        f"Current price: {detail.current_price or 'Unavailable'} {detail.currency or ''}",
                        f"Volume: {detail.volume or 'Unavailable'}",
                        f"Market cap: {detail.market_cap or 'Unavailable'}",
                        f"P/E ratio: {detail.pe_ratio or 'Unavailable'}",
                    ]
                )
            )
        except Exception:
            context_sections.append(f"Stock: {ticker}\nCompany data unavailable.")

        try:
            news = await stock_service.get_stock_news(ticker, 5)
            article_lines = [
                (
                    f"- {article.headline} | Source: {article.source or 'Unknown'} | "
                    f"Date: {article.publish_date or 'Unknown'} | "
                    f"Sentiment: {article.sentiment_label} ({article.sentiment_score}) | "
                    f"Summary: {article.summary or 'Unavailable'}"
                )
                for article in news.articles
            ]
            context_sections.append(f"Recent {ticker} news:\n" + "\n".join(article_lines))
        except Exception:
            context_sections.append(f"Recent {ticker} news unavailable.")

    if not context_sections:
        return "No specific ticker was detected. Answer generally and ask for a ticker if needed."

    return "\n\n".join(context_sections)


def _build_instructions() -> str:
    return (
        "You are the AI financial assistant inside AI Stock Intelligence Platform. "
        "Use the provided stock and news context when answering. Be concise, practical, "
        "and transparent about uncertainty. Do not provide personalized financial advice, "
        "buy/sell instructions, price targets, or guarantees. Always remind the user that "
        "the response is informational research support and that they should verify data "
        "before investing."
    )


def _build_prompt(user_content: str, context: str) -> str:
    return (
        "User question:\n"
        f"{user_content}\n\n"
        "Available platform context:\n"
        f"{context}\n\n"
        "Answer using only this context and clearly state when information is unavailable."
    )


async def create_message_exchange(
    session: AsyncSession,
    user_id: int,
    session_id: int,
    message_create: ChatMessageCreate,
) -> ChatExchangeResponse:
    chat_session = await _get_owned_session(session, user_id, session_id)

    user_message = ChatMessage(
        session_id=session_id,
        role="user",
        content=message_create.content.strip(),
    )
    session.add(user_message)
    await session.flush()

    context = await _build_market_context(message_create.content)
    assistant_content = await openai_service.generate_assistant_response(
        prompt=_build_prompt(message_create.content, context),
        instructions=_build_instructions(),
    )

    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_content,
    )
    session.add(assistant_message)

    if chat_session.title == "New AI chat":
        chat_session.title = _build_title(message_create.content)
    chat_session.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(chat_session)
    await session.refresh(user_message)
    await session.refresh(assistant_message)

    return ChatExchangeResponse(
        session=_session_to_read(chat_session),
        user_message=_message_to_read(user_message),
        assistant_message=_message_to_read(assistant_message),
    )
