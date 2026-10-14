from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


STREAM_TOKEN_SCOPE = "market_stream"
STREAM_TOKEN_TTL_SECONDS = 120


def create_stream_token(subject: str) -> str:
    """Short-lived token that only authorizes opening the market WebSocket.

    Browsers cannot send the auth cookie to a backend on a different domain, so the
    frontend fetches this token through its same-origin API proxy and passes it in
    the WebSocket URL instead.
    """
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(seconds=STREAM_TOKEN_TTL_SECONDS)
    payload = {"sub": subject, "exp": expires_at, "scope": STREAM_TOKEN_SCOPE}

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
