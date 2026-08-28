"""Integration health monitoring."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.credentials.store import credential_store


class IntegrationStatus(StrEnum):
    CONNECTED = "CONNECTED"
    NOT_CONNECTED = "NOT_CONNECTED"
    READY = "READY"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class IntegrationHealth(BaseModel):
    name: str
    status: IntegrationStatus
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthReport(BaseModel):
    overall: str = "ok"
    integrations: list[IntegrationHealth] = Field(default_factory=list)


def check_integrations(user_id: str = "default") -> HealthReport:
    items: list[IntegrationHealth] = []

    from app.config import get_settings

    settings = get_settings()
    if settings.default_llm_provider == "mock":
        items.append(IntegrationHealth(name="llm", status=IntegrationStatus.READY, detail="mock"))
    elif settings.anthropic_api_key or settings.openai_api_key:
        items.append(
            IntegrationHealth(
                name="llm",
                status=IntegrationStatus.CONNECTED,
                detail=settings.default_llm_provider,
            )
        )
    else:
        items.append(
            IntegrationHealth(name="llm", status=IntegrationStatus.NOT_CONNECTED, detail="no API keys")
        )

    if settings.database_url:
        items.append(
            IntegrationHealth(name="database", status=IntegrationStatus.READY, detail="url configured")
        )
    else:
        items.append(IntegrationHealth(name="database", status=IntegrationStatus.NOT_CONNECTED))

    for name in ("gmail", "calendar", "telegram", "whatsapp"):
        if credential_store.has(user_id, name) or (
            name == "telegram" and settings.telegram_bot_token
        ):
            items.append(IntegrationHealth(name=name, status=IntegrationStatus.CONNECTED))
        else:
            items.append(IntegrationHealth(name=name, status=IntegrationStatus.NOT_CONNECTED))

    items.append(
        IntegrationHealth(name="browser", status=IntegrationStatus.READY, detail="playwright optional")
    )
    items.append(
        IntegrationHealth(name="computer", status=IntegrationStatus.READY, detail="policy-gated")
    )

    overall = "ok"
    if any(i.status == IntegrationStatus.ERROR for i in items):
        overall = "degraded"
    return HealthReport(overall=overall, integrations=items)
