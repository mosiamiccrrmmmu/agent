from __future__ import annotations

"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Personal AI Agent"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = Field(..., min_length=16)

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = Field(
        ...,
        description="Async PostgreSQL connection string (postgresql+asyncpg://...)",
    )
    database_url_sync: str = Field(
        ...,
        description="Sync PostgreSQL connection string for Alembic",
    )

    # LLM
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    default_llm_provider: Literal["anthropic", "openai", "mock"] = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "claude-3-5-haiku-20241022"
    coding_model: str = "claude-sonnet-4-20250514"
    openai_default_model: str = "gpt-4o"
    openai_fast_model: str = "gpt-4o-mini"

    # Agent Runtime
    max_agent_steps: int = 15
    agent_timeout_seconds: int = 120
    max_tool_retries: int = 2

    # Memory
    short_term_max_messages: int = 50
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Permissions
    require_approval_for_high_risk: bool = True
    require_approval_for_critical: bool = True

    # Telegram
    telegram_bot_token: str | None = None
    telegram_allowed_user_ids: str = ""

    # Observability
    enable_cost_tracking: bool = True

    @field_validator("telegram_allowed_user_ids", mode="before")
    @classmethod
    def parse_allowed_ids(cls, v: str | list[int] | None) -> str:
        if v is None:
            return ""
        if isinstance(v, list):
            return ",".join(str(i) for i in v)
        return str(v)

    @property
    def allowed_telegram_user_ids(self) -> list[int]:
        if not self.telegram_allowed_user_ids.strip():
            return []
        return [int(x.strip()) for x in self.telegram_allowed_user_ids.split(",") if x.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()  # type: ignore[call-arg]
