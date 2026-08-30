"""Local LLM provider abstraction — Ollama / llama.cpp / Windows ML later."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMResponse, LLMUsage, Message, ToolDefinition

logger = get_logger(__name__)


class LocalProvider(LLMProvider):
    """Offline foundation. Returns structured unavailable until a backend is wired."""

    name = "local"

    def __init__(self, *, backend: str = "none", model: str = "local") -> None:
        self.backend = backend
        self.model = model

    async def generate(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        logger.warning("local_llm_not_configured", backend=self.backend)
        return LLMResponse(
            content=(
                "LOCAL_AI_UNAVAILABLE: Local LLM backend is not configured. "
                "Install Ollama or another backend and set LOCAL_LLM_URL."
            ),
            model=model or self.model,
            usage=LLMUsage(),
            finish_reason="error",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        yield "LOCAL_AI_UNAVAILABLE"
