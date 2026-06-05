from fastapi.testclient import TestClient

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
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
