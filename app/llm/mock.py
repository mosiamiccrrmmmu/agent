"""Mock LLM Provider for testing without real API keys."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.llm.base import (
    LLMProvider,
    LLMResponse,
    LLMUsage,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
)


class MockLLMProvider(LLMProvider):
    """Deterministic mock for unit/integration tests."""

    name = "mock"

    def __init__(self, default_response: str = "This is a mock response.") -> None:
        self.default_response = default_response
        self.calls: list[dict[str, Any]] = []
        self._tool_called = False

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
        self.calls.append(
            {
                "messages_count": len(messages),
                "model": model,
                "has_tools": bool(tools),
            }
        )

        has_tool_result = any(m.role == MessageRole.TOOL for m in messages)
        if has_tool_result or self._tool_called:
            self._tool_called = False
            return LLMResponse(
                content="I searched and here is a summary based on the tool result.",
                tool_calls=[],
                usage=LLMUsage(input_tokens=20, output_tokens=15, total_tokens=35),
                model=model or "mock-model",
                finish_reason="end_turn",
            )

        last_user = next(
            (m for m in reversed(messages) if m.role == MessageRole.USER), None
        )
        content = (last_user.content or "") if last_user else ""

        if "search" in content.lower() and tools:
            search_tool = next((t for t in tools if t.name == "search_web"), None)
            if search_tool:
                self._tool_called = True
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="mock_tool_1",
                            name="search_web",
                            arguments={"query": "test query"},
                        )
                    ],
                    usage=LLMUsage(input_tokens=10, output_tokens=5, total_tokens=15),
                    model=model or "mock-model",
                    finish_reason="tool_use",
                )

        return LLMResponse(
            content=self.default_response,
            tool_calls=[],
            usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            model=model or "mock-model",
            finish_reason="end_turn",
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
        for word in self.default_response.split():
            yield word + " "
