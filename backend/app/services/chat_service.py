import re
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatMessageSource, ChatSession
from app.schemas.chat import (
    ChatExchangeResponse,
    ChatMessageCreate,
    ChatMessageRead,
    ChatSourceRead,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionRead,
)
from app.services import openai_service, prediction_service, stock_service, tavily_service

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


@dataclass(frozen=True)
class MarketContext:
    context: str
    sources: list[ChatSourceRead]
    symbols: list[str]


def _session_to_read(session: ChatSession) -> ChatSessionRead:
    return ChatSessionRead(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _message_to_read(
    message: ChatMessage,
    sources: list[ChatSourceRead] | None = None,
) -> ChatMessageRead:
    source_list = sources or []
    stock_symbol = source_list[0].stock_symbol if source_list else None
    return ChatMessageRead(
        id=message.id,
        role=message.role,  # type: ignore[arg-type]
        content=message.content,
        created_at=message.created_at,
        stock_symbol=stock_symbol,
        sources=source_list,
    )


def _build_title(content: str) -> str:
    title = " ".join(content.strip().split())
    return title[:80] if title else "New AI chat"


def _is_prediction_question(content: str) -> bool:
    lowered_content = content.lower()
    prediction_terms = ("prediction", "predict", "bullish", "bearish", "model", "expects", "expected", "increase", "decrease")
    return any(term in lowered_content for term in prediction_terms)

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


async def _recent_session_symbols(session: AsyncSession, session_id: int) -> list[str]:
    result = await session.execute(
        select(ChatMessageSource.stock_symbol)
        .join(ChatMessage, ChatMessage.id == ChatMessageSource.message_id)
        .where(
            ChatMessage.session_id == session_id,
            ChatMessageSource.stock_symbol.is_not(None),
        )
        .order_by(ChatMessageSource.created_at.desc())
        .limit(3)
    )
    symbols = []
    for symbol in result.scalars().all():
        if symbol and symbol not in symbols:
            symbols.append(symbol)

    return symbols


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
    messages = list(result.scalars().all())

    source_result = await session.execute(
        select(ChatMessageSource).where(
            ChatMessageSource.message_id.in_([message.id for message in messages] or [0])
        )
    )
    sources_by_message_id: dict[int, list[ChatSourceRead]] = {}
    for source in source_result.scalars().all():
        sources_by_message_id.setdefault(source.message_id, []).append(
            ChatSourceRead(
                id=source.id,
                stock_symbol=source.stock_symbol,
                source_name=source.source_name,
                title=source.title,
                published_at=source.published_at,
                url=source.url,
            )
        )

    return ChatSessionDetail(
        **_session_to_read(chat_session).model_dump(),
        messages=[
            _message_to_read(message, sources_by_message_id.get(message.id, []))
            for message in messages
        ],
    )


async def delete_session(
    session: AsyncSession,
    user_id: int,
    session_id: int,
) -> None:
    chat_session = await _get_owned_session(session, user_id, session_id)
    message_ids_result = await session.execute(
        select(ChatMessage.id).where(ChatMessage.session_id == session_id)
    )
    message_ids = list(message_ids_result.scalars().all())

    if message_ids:
        await session.execute(
            delete(ChatMessageSource).where(ChatMessageSource.message_id.in_(message_ids))
        )
        await session.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))

    await session.delete(chat_session)
    await session.commit()

def _source_line(source: ChatSourceRead, detail: str | None = None) -> str:
    suffix = f" | Detail: {detail}" if detail else ""
    return (
        f"- Source: {source.source_name} | Title: {source.title} | "
        f"Date: {source.published_at or 'Unknown'} | URL: {source.url or 'Unavailable'}{suffix}"
    )


async def _build_market_context(
    session: AsyncSession,
    content: str,
    fallback_symbols: list[str] | None = None,
) -> MarketContext:
    tickers = _extract_tickers(content) or (fallback_symbols or [])
    context_sections: list[str] = []
    sources: list[ChatSourceRead] = []

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

        if _is_prediction_question(content):
            prediction_context = await prediction_service.get_prediction_explanation_context(session, ticker)
            context_sections.append(f"Prediction context for {ticker}:\n{prediction_context}")

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
            for article in news.articles:
                sources.append(
                    ChatSourceRead(
                        stock_symbol=ticker,
                        source_name=article.source or "Yahoo Finance",
                        title=article.headline,
                        published_at=article.publish_date,
                        url=article.url,
                    )
                )
            context_sections.append(f"Recent {ticker} news:\n" + "\n".join(article_lines))
        except Exception:
            context_sections.append(f"Recent {ticker} news unavailable.")

        web_results = await tavily_service.search_market_news(
            f"{ticker} stock latest investor concerns earnings analyst news",
            max_results=5,
        )
        if web_results:
            web_lines = []
            for result in web_results:
                source = ChatSourceRead(
                    stock_symbol=ticker,
                    source_name=result.source_name,
                    title=result.title,
                    published_at=result.published_at,
                    url=result.url,
                )
                sources.append(source)
                web_lines.append(_source_line(source, result.content))
            context_sections.append(f"Web research for {ticker}:\n" + "\n".join(web_lines))

    if not context_sections:
        return MarketContext(
            context="No specific ticker was detected. Ask the user for the company or ticker before analyzing.",
            sources=[],
            symbols=[],
        )

    return MarketContext(
        context="\n\n".join(context_sections),
        sources=sources[:12],
        symbols=tickers,
    )


def _build_instructions() -> str:
    return (
        "You are the AI financial assistant inside AI Stock Intelligence Platform. "
        "You must answer only from retrieved platform context and cited sources. "
        "Do not answer from memory. If context is missing, say what is missing. "
        "Use this exact structure: Summary, Key Factors, Market Sentiment, Risks, "
        "Recent Developments, Sources, Confidence Score. Be concise, practical, "
        "and transparent about uncertainty. Do not provide personalized financial advice, "
        "buy/sell instructions, price targets, or guarantees."
    )


def _build_prompt(user_content: str, context: str) -> str:
    return (
        "User question:\n"
        f"{user_content}\n\n"
        "Available platform context:\n"
        f"{context}\n\n"
        "Answer using only this retrieved context. Include source names in the Sources section. "
        "End with a reminder that this is informational research support, not financial advice."
    )


def _persist_message_sources(
    session: AsyncSession,
    assistant_message: ChatMessage,
    market_context: MarketContext,
) -> None:
    for source in market_context.sources:
        session.add(
            ChatMessageSource(
                message_id=assistant_message.id,
                stock_symbol=source.stock_symbol,
                source_name=source.source_name,
                title=source.title[:500],
                published_at=source.published_at,
                url=source.url,
            )
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

    fallback_symbols = await _recent_session_symbols(session, session_id)
    market_context = await _build_market_context(session, message_create.content, fallback_symbols)
    assistant_content = await openai_service.generate_assistant_response(
        prompt=_build_prompt(message_create.content, market_context.context),
        instructions=_build_instructions(),
    )

    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_content,
    )
    session.add(assistant_message)
    await session.flush()
    _persist_message_sources(session, assistant_message, market_context)

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
        assistant_message=_message_to_read(
            assistant_message,
            market_context.sources,
        ),
    )
