from __future__ import annotations

"""Anthropic Claude provider implementation."""

from collections.abc import AsyncIterator
from typing import Any

import anthropic
from anthropic.types import Message as AnthropicMessage
from anthropic.types import TextBlock, ToolUseBlock

from app.core.logging import get_logger
from app.llm.base import (
    LLMProvider,
    LLMResponse,
    LLMUsage,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
)

logger = get_logger(__name__)

PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING.get(model, {"input": 3.0, "output": 15.0})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-20250514") -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for AnthropicProvider")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.default_model = default_model

    def _convert_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system: str | None = None
        converted: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system = (system or "") + (msg.content or "")
                continue
            if msg.role == MessageRole.USER:
                converted.append({"role": "user", "content": msg.content or ""})
            elif msg.role == MessageRole.ASSISTANT:
                content_blocks: list[dict[str, Any]] = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        content_blocks.append(
                            {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                        )
                converted.append({"role": "assistant", "content": content_blocks or ""})
            elif msg.role == MessageRole.TOOL:
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg.tool_call_id or "",
                                "content": msg.content or "",
                            }
                        ],
                    }
                )
        return system, converted

    def _convert_tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in tools
        ]

    def _parse_response(self, response: AnthropicMessage, model: str) -> LLMResponse:
        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if isinstance(block, TextBlock):
                content_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )
        usage = LLMUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            estimated_cost_usd=_estimate_cost(
                model, response.usage.input_tokens, response.usage.output_tokens
            ),
        )
        return LLMResponse(
            content="".join(content_parts) if content_parts else None,
            tool_calls=tool_calls,
            usage=usage,
            model=model,
            finish_reason=response.stop_reason,
            raw=response,
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
        model = model or self.default_model
        system, converted = self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        if stop:
            kwargs["stop_sequences"] = stop
        logger.debug("anthropic_generate", model=model, tool_count=len(anthropic_tools or []))
        response = await self.client.messages.create(**kwargs)
        return self._parse_response(response, model)

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        model = model or self.default_model
        system, converted = self._convert_messages(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def close(self) -> None:
        await self.client.close()
