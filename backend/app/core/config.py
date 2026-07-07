import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Stock Intelligence Platform API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://stock_user:stock_password@localhost:5432/stock_intelligence"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    auth_cookie_name: str = "access_token"
    auth_cookie_secure: bool = False
    auto_create_tables: bool = False
    huggingface_api_token: str | None = None
    huggingface_sentiment_model: str = "ProsusAI/finbert"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    finnhub_api_key: str | None = None
    tavily_api_key: str | None = None
    tavily_search_depth: str = "basic"
    ml_scheduler_enabled: bool = True
    ml_retrain_interval_days: int = 4
    ml_scheduler_initial_delay_seconds: int = 30
    ml_models_dir: str = "models"
    ml_default_symbols: str = "AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL,META,JPM"
    ml_min_training_rows: int = 120

    @property
    def cors_origins(self) -> list[str]:
        value = self.backend_cors_origins.strip()
        if value.startswith("["):
            parsed_value = json.loads(value)
            if isinstance(parsed_value, list):
                return [str(origin).strip() for origin in parsed_value if str(origin).strip()]

        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def default_ml_symbols(self) -> list[str]:
        return [symbol.strip().upper() for symbol in self.ml_default_symbols.split(",") if symbol.strip()]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

