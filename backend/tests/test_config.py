import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            app_env="production",
            jwt_secret_key="replace-with-long-random-secret",
            auth_cookie_secure=True,
            _env_file=None,
        )


def test_production_requires_secure_cookie() -> None:
    with pytest.raises(ValidationError, match="AUTH_COOKIE_SECURE"):
        Settings(
            app_env="production",
            jwt_secret_key="x" * 48,
            auth_cookie_secure=False,
            _env_file=None,
        )


def test_development_allows_default_settings() -> None:
    settings = Settings(app_env="development", _env_file=None)

    assert settings.app_env == "development"
