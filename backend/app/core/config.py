import json
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Stock Portfolio Analytics API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:3000"
    database_url: str = (
        "postgresql+asyncpg://stock_user:stock_password@localhost:5432/stock_intelligence"
    )
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    auth_cookie_name: str = "access_token"
    auth_cookie_secure: bool = False
    demo_mode_enabled: bool = True
    finnhub_api_key: str | None = None

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_url(cls, value: str) -> str:
        """Accept URLs as hosting providers show them (e.g. Neon, Render) and adapt for asyncpg."""
        parts = urlsplit(value)
        scheme = parts.scheme
        if scheme in ("postgres", "postgresql"):
            scheme = "postgresql+asyncpg"

        query = []
        for key, item in parse_qsl(parts.query):
            if key == "sslmode":
                # asyncpg spells this option "ssl".
                query.append(("ssl", item))
            elif key != "channel_binding":
                # asyncpg does not accept channel_binding.
                query.append((key, item))

        return urlunsplit(parts._replace(scheme=scheme, query=urlencode(query)))

    @model_validator(mode="after")
    def _require_production_secrets(self) -> "Settings":
        if self.app_env != "production":
            return self

        if len(self.jwt_secret_key) < 32 or self.jwt_secret_key.startswith(
            ("change-me", "replace-with")
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be set to a random value of at least 32 characters."
            )

        if not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE must be true in production.")

        return self

    @property
    def cors_origins(self) -> list[str]:
        value = self.backend_cors_origins.strip()
        if value.startswith("["):
            parsed_value = json.loads(value)
            if isinstance(parsed_value, list):
                return [str(origin).strip() for origin in parsed_value if str(origin).strip()]

        return [origin.strip() for origin in value.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
