from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User
from app.schemas.chat import (
    ChatExchangeResponse,
    ChatMessageCreate,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionRead,
)
from app.services import chat_service

client = TestClient(app)


def override_current_user() -> User:
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        password_hash="hashed",
        created_at=datetime.now(UTC),
    )


def build_session() -> ChatSessionRead:
    now = datetime.now(UTC)
    return ChatSessionRead(
        id=1,
        title="Why did Tesla move today?",
        created_at=now,
        updated_at=now,
    )


def build_message(message_id: int, role: str, content: str) -> ChatMessageRead:
    return ChatMessageRead(
        id=message_id,
        role=role,  # type: ignore[arg-type]
        content=content,
        created_at=datetime.now(UTC),
    )


def test_chat_requires_authentication() -> None:
    response = client.get("/api/v1/chat/sessions")

    assert response.status_code == 401


def test_create_chat_session(monkeypatch) -> None:
    async def fake_create_session(
        session,
        user_id: int,
        session_create: ChatSessionCreate,
    ) -> ChatSessionRead:
        assert user_id == 1
        assert session_create.title == "Tesla research"
        return build_session()

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(chat_service, "create_session", fake_create_session)

    response = client.post("/api/v1/chat/sessions", json={"title": "Tesla research"})

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["title"] == "Why did Tesla move today?"


def test_read_chat_session(monkeypatch) -> None:
    async def fake_get_session_detail(session, user_id: int, session_id: int) -> ChatSessionDetail:
        assert user_id == 1
        assert session_id == 1
        return ChatSessionDetail(
            **build_session().model_dump(),
            messages=[
                build_message(1, "user", "Summarize Nvidia news."),
                build_message(2, "assistant", "Nvidia news is broadly positive."),
            ],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(chat_service, "get_session_detail", fake_get_session_detail)

    response = client.get("/api/v1/chat/sessions/1")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["messages"][1]["role"] == "assistant"


def test_delete_chat_session(monkeypatch) -> None:
    async def fake_delete_session(session, user_id: int, session_id: int) -> None:
        assert user_id == 1
        assert session_id == 1

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(chat_service, "delete_session", fake_delete_session)

    response = client.delete("/api/v1/chat/sessions/1")

    app.dependency_overrides.clear()

    assert response.status_code == 204

def test_create_chat_message(monkeypatch) -> None:
    async def fake_create_message_exchange(
        session,
        user_id: int,
        session_id: int,
        message_create: ChatMessageCreate,
    ) -> ChatExchangeResponse:
        assert user_id == 1
        assert session_id == 1
        assert message_create.content == "What is Apple's current sentiment?"
        return ChatExchangeResponse(
            session=build_session(),
            user_message=build_message(1, "user", message_create.content),
            assistant_message=build_message(
                2,
                "assistant",
                "Apple sentiment is neutral based on the available headlines.",
            ),
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(chat_service, "create_message_exchange", fake_create_message_exchange)

    response = client.post(
        "/api/v1/chat/sessions/1/messages",
        json={"content": "What is Apple's current sentiment?"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_message"]["role"] == "user"
    assert payload["assistant_message"]["role"] == "assistant"


def test_extract_tickers_understands_company_names_without_common_words() -> None:
    tickers = chat_service._extract_tickers("what is tesla stock currently doing good or not?")

    assert tickers == ["TSLA"]


async def test_build_market_context_includes_prediction_context(monkeypatch) -> None:
    async def unavailable(*_args, **_kwargs):
        raise RuntimeError("upstream unavailable")

    async def fake_prediction_context(_session, ticker: str) -> str:
        return f"{ticker} prediction evidence"

    async def no_web_results(*_args, **_kwargs):
        return []

    monkeypatch.setattr(chat_service.stock_service, "get_stock_detail", unavailable)
    monkeypatch.setattr(chat_service.stock_service, "get_stock_news", unavailable)
    monkeypatch.setattr(
        chat_service.prediction_service,
        "get_prediction_explanation_context",
        fake_prediction_context,
    )
    monkeypatch.setattr(chat_service.tavily_service, "search_market_news", no_web_results)

    market_context = await chat_service._build_market_context(
        object(),  # type: ignore[arg-type]
        "What does the model predict for $NVDA?",
    )

    assert market_context.symbols == ["NVDA"]
    assert "NVDA prediction evidence" in market_context.context
