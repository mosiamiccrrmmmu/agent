"""Model router — explicit provider selection, never silent switch."""

from __future__ import annotations

from enum import StrEnum

from app.config import get_settings
from app.core.logging import get_logger
from app.llm.base import LLMProvider
from app.llm.factory import LLMFactory, llm_factory

logger = get_logger(__name__)


class RouteReason(StrEnum):
    DEFAULT = "default"
    EXPLICIT = "explicit"
    FALLBACK_REQUESTED = "fallback_requested"
    OFFLINE = "offline"
    NOT_CONFIGURED = "not_configured"


class RouteDecision:
    def __init__(self, provider_name: str, reason: RouteReason, detail: str = "") -> None:
        self.provider_name = provider_name
        self.reason = reason
        self.detail = detail


class ModelRouter:
    def __init__(self, factory: LLMFactory | None = None) -> None:
        self.factory = factory or llm_factory

    def decide(
        self,
        *,
        preferred: str | None = None,
        offline: bool = False,
        allow_fallback: bool = False,
    ) -> RouteDecision:
        settings = get_settings()
        if offline:
            return RouteDecision("local", RouteReason.OFFLINE, "offline mode requested")
        name = (preferred or settings.default_llm_provider or "grok").lower()
        if name == "grok" and not settings.effective_xai_api_key:
            if allow_fallback:
                return RouteDecision(
                    "mock",
                    RouteReason.FALLBACK_REQUESTED,
                    "Grok key missing; fallback allowed",
                )
            return RouteDecision(
                "grok",
                RouteReason.NOT_CONFIGURED,
                "XAI_API_KEY not set",
            )
        return RouteDecision(
            name, RouteReason.DEFAULT if not preferred else RouteReason.EXPLICIT
        )

    def get_provider(
        self,
        *,
        preferred: str | None = None,
        offline: bool = False,
        allow_fallback: bool = False,
    ) -> tuple[LLMProvider, RouteDecision]:
        decision = self.decide(
            preferred=preferred, offline=offline, allow_fallback=allow_fallback
        )
        provider = self.factory.get_provider(decision.provider_name)
        logger.info(
            "model_routed",
            provider=decision.provider_name,
            reason=decision.reason.value,
            detail=decision.detail,
        )
        return provider, decision


model_router = ModelRouter()
