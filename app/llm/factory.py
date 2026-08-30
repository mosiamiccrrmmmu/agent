from __future__ import annotations

"""LLM Provider factory and simple model router.

Supported providers: grok (primary), openai, anthropic, local, mock.
"""

from enum import StrEnum

from app.config import get_settings
from app.core.logging import get_logger
from app.llm.anthropic import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.grok import GrokProvider
from app.llm.local import LocalProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai import OpenAIProvider

logger = get_logger(__name__)


class TaskType(StrEnum):
    GENERAL = "general"
    REASONING = "reasoning"
    CODING = "coding"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    FAST = "fast"


class LLMFactory:
    """Creates and caches LLM provider instances."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def get_provider(self, name: str | None = None) -> LLMProvider:
        settings = get_settings()
        provider_name = (name or settings.default_llm_provider).lower()

        if provider_name in self._providers:
            return self._providers[provider_name]

        if provider_name == "grok":
            api_key = settings.effective_xai_api_key
            if not api_key:
                raise RuntimeError(
                    "XAI_API_KEY (or GROK_API_KEY) is not configured for Grok provider"
                )
            provider: LLMProvider = GrokProvider(
                api_key=api_key,
                default_model=settings.grok_default_model or settings.default_model,
            )
        elif provider_name == "anthropic":
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not configured")
            provider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                default_model=settings.anthropic_default_model or settings.default_model,
            )
        elif provider_name == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                default_model=settings.openai_default_model,
            )
        elif provider_name == "local":
            provider = LocalProvider()
        elif provider_name == "mock":
            provider = MockLLMProvider()
        else:
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Supported: grok, openai, anthropic, local, mock"
            )

        self._providers[provider_name] = provider
        logger.info("llm_provider_initialized", provider=provider_name)
        return provider

    def resolve_model(
        self, task: TaskType = TaskType.GENERAL, provider_name: str | None = None
    ) -> tuple[LLMProvider, str]:
        settings = get_settings()
        provider = self.get_provider(provider_name)

        if provider.name == "mock":
            return provider, "mock-model"
        if provider.name == "local":
            return provider, "local"

        if provider.name == "grok":
            model_map = {
                TaskType.GENERAL: settings.grok_default_model,
                TaskType.REASONING: settings.grok_default_model,
                TaskType.CODING: settings.coding_model,
                TaskType.SUMMARIZATION: settings.grok_fast_model,
                TaskType.CLASSIFICATION: settings.grok_fast_model,
                TaskType.FAST: settings.grok_fast_model,
            }
        elif provider.name == "anthropic":
            model_map = {
                TaskType.GENERAL: settings.anthropic_default_model,
                TaskType.REASONING: settings.anthropic_default_model,
                TaskType.CODING: settings.anthropic_default_model,
                TaskType.SUMMARIZATION: settings.anthropic_fast_model,
                TaskType.CLASSIFICATION: settings.anthropic_fast_model,
                TaskType.FAST: settings.anthropic_fast_model,
            }
        else:
            model_map = {
                TaskType.GENERAL: settings.openai_default_model,
                TaskType.REASONING: settings.openai_default_model,
                TaskType.CODING: settings.openai_default_model,
                TaskType.SUMMARIZATION: settings.openai_fast_model,
                TaskType.CLASSIFICATION: settings.openai_fast_model,
                TaskType.FAST: settings.openai_fast_model,
            }

        model = model_map.get(task, settings.default_model)
        return provider, model or settings.default_model

    async def close_all(self) -> None:
        for p in self._providers.values():
            close = getattr(p, "close", None)
            if close:
                await close()
        self._providers.clear()

    def clear(self) -> None:
        self._providers.clear()

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        self._providers[name] = provider


llm_factory = LLMFactory()
