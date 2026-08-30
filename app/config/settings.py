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
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production", "desktop"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = Field(default="dev-secret-key-change-me", min_length=16)
    desktop_mode: bool = False

    # Server — desktop launcher overrides to 127.0.0.1
    host: str = "127.0.0.1"
    port: int = 8765

    # Database (SQLite for desktop; Postgres optional for server)
    database_url: str = Field(
        default="sqlite+aiosqlite:///./personal_ai.db",
        description="Async DB URL (sqlite+aiosqlite://... or postgresql+asyncpg://...)",
    )
    database_url_sync: str = Field(
        default="sqlite:///./personal_ai.db",
        description="Sync DB URL for migrations",
    )

    # LLM — Grok is the primary desktop provider
    xai_api_key: str | None = Field(default=None, validation_alias="XAI_API_KEY")
    grok_api_key: str | None = Field(default=None, validation_alias="GROK_API_KEY")
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    default_llm_provider: Literal["grok", "openai", "anthropic", "mock"] = "grok"
    default_model: str = "grok-3-mini"
    fast_model: str = "grok-3-mini"
    coding_model: str = "grok-3-mini"
    grok_default_model: str = "grok-3-mini"
    grok_fast_model: str = "grok-3-mini"
    openai_default_model: str = "gpt-4o"
    openai_fast_model: str = "gpt-4o-mini"
    anthropic_default_model: str = "claude-sonnet-4-20250514"
    anthropic_fast_model: str = "claude-3-5-haiku-20241022"

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
    telegram_webhook_secret: str | None = None

    # Observability
    enable_cost_tracking: bool = True

    # Local auth (desktop)
    require_local_auth: bool = True

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

    @property
    def is_desktop(self) -> bool:
        return self.desktop_mode or self.app_env == "desktop"

    @property
    def effective_xai_api_key(self) -> str | None:
        """Prefer XAI_API_KEY, fall back to GROK_API_KEY."""
        return self.xai_api_key or self.grok_api_key


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
