from fastapi.testclient import TestClient

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.main import app

client = TestClient(app)


def test_protected_route_requires_authentication() -> None:
    response = client.get("/api/v1/auth/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_password_hashing_and_verification() -> None:
    password_hash = hash_password("secure-password-123")

    assert password_hash != "secure-password-123"
    assert verify_password("secure-password-123", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_contains_subject() -> None:
    access_token = create_access_token(subject="123")
    payload = decode_access_token(access_token)

    assert payload["sub"] == "123"


def test_demo_login_sets_auth_cookie(monkeypatch) -> None:
    from datetime import UTC, datetime

    from app.core.config import get_settings
    from app.models.user import User
    from app.services import demo_service

    async def fake_get_or_create_demo_user(_session) -> User:
        return User(
            id=42,
            name="Demo Investor",
            email="demo@stockintel.app",
            password_hash="hashed",
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(demo_service, "get_or_create_demo_user", fake_get_or_create_demo_user)

    response = client.post("/api/v1/auth/demo")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "demo@stockintel.app"
    assert get_settings().auth_cookie_name in response.cookies


def test_demo_login_can_be_disabled(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "demo_mode_enabled", False)

    response = client.post("/api/v1/auth/demo")

    assert response.status_code == 404


def test_login_is_rate_limited() -> None:
    from app.core.rate_limit import login_rate_limit

    for _ in range(login_rate_limit.max_requests):
        login_rate_limit.check("testclient")

    response = client.post(
        "/api/v1/auth/login", json={"email": "someone@example.com", "password": "password123"}
    )

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1
