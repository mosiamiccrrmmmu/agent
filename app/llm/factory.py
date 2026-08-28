from __future__ import annotations

"""LLM Provider factory and simple model router."""

from enum import StrEnum

from app.config import get_settings
from app.core.logging import get_logger
from app.llm.anthropic import AnthropicProvider
from app.llm.base import LLMProvider
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
        provider_name = name or settings.default_llm_provider

        if provider_name in self._providers:
            return self._providers[provider_name]

        if provider_name == "anthropic":
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not configured")
            provider: LLMProvider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                default_model=settings.default_model,
            )
        elif provider_name == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                default_model=settings.openai_default_model,
            )
        elif provider_name == "mock":
            provider = MockLLMProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

        self._providers[provider_name] = provider
        logger.info("llm_provider_initialized", provider=provider_name)
        return provider

    def resolve_model(
        self, task: TaskType = TaskType.GENERAL, provider_name: str | None = None
    ) -> tuple[LLMProvider, str]:
        """Simple model routing based on task type."""
        settings = get_settings()
        provider = self.get_provider(provider_name)

        if provider.name == "mock":
            return provider, "mock-model"

        if provider.name == "anthropic":
            model_map = {
                TaskType.GENERAL: settings.default_model,
                TaskType.REASONING: settings.default_model,
                TaskType.CODING: settings.coding_model,
                TaskType.SUMMARIZATION: settings.fast_model,
                TaskType.CLASSIFICATION: settings.fast_model,
                TaskType.FAST: settings.fast_model,
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
        return provider, model

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        """Allow tests to inject a custom provider."""
        self._providers[name] = provider

    async def close_all(self) -> None:
        for p in self._providers.values():
            await p.close()
        self._providers.clear()


llm_factory = LLMFactory()
