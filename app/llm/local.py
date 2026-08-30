"""Local LLM provider — Ollama-compatible HTTP when configured."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx

from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMResponse, LLMUsage, Message, ToolDefinition

logger = get_logger(__name__)


class LocalProvider(LLMProvider):
    """Offline foundation. Uses Ollama chat API if reachable; else LOCAL_AI_UNAVAILABLE."""

    name = "local"

    def __init__(
        self,
        *,
        backend: str = "ollama",
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.backend = backend
        self.model = model or os.environ.get("LOCAL_AI_MODEL", "llama3.2")
        self.base_url = (
            base_url
            or os.environ.get("LOCAL_AI_BASE_URL")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self._enabled = os.environ.get("LOCAL_AI_ENABLED", "true").lower() in (
            "1",
            "true",
            "yes",
        )

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
        if not self._enabled:
            return LLMResponse(
                content="LOCAL_AI_UNAVAILABLE: LOCAL_AI_ENABLED is false.",
                model=model or self.model,
                usage=LLMUsage(),
                finish_reason="error",
            )
        use_model = model or self.model
        payload = {
            "model": use_model,
            "messages": [
                {"role": m.role.value, "content": m.content or ""} for m in messages
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code >= 400:
                    return LLMResponse(
                        content=(
                            f"LOCAL_AI_UNAVAILABLE: backend HTTP {resp.status_code}. "
                            "Install Ollama or set LOCAL_AI_BASE_URL."
                        ),
                        model=use_model,
                        usage=LLMUsage(),
                        finish_reason="error",
                    )
                data = resp.json()
                content = (data.get("message") or {}).get("content") or ""
                return LLMResponse(
                    content=content,
                    model=use_model,
                    usage=LLMUsage(),
                    finish_reason="stop",
                )
        except Exception as exc:
            logger.warning("local_llm_unavailable", error=str(exc))
            return LLMResponse(
                content=(
                    "LOCAL_AI_UNAVAILABLE: Local LLM backend is not reachable. "
                    "Install Ollama (or compatible) and set LOCAL_AI_BASE_URL."
                ),
                model=use_model,
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
        resp = await self.generate(
            messages,
            model=model,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield resp.content or "LOCAL_AI_UNAVAILABLE"
