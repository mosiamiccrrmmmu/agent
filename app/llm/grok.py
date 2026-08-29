from __future__ import annotations

"""Grok (xAI) provider — primary LLM for Personal AI.

Uses the OpenAI-compatible Chat Completions API at https://api.x.ai/v1
so the Agent Core stays provider-agnostic.
"""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage

from app.core.logging import get_logger
from app.llm.base import (
    LLMProvider,
    LLMResponse,
    LLMUsage,
    Message,
    ToolCall,
    ToolDefinition,
)

logger = get_logger(__name__)

PRICING: dict[str, dict[str, float]] = {
    "grok-2": {"input": 2.0, "output": 10.0},
    "grok-2-latest": {"input": 2.0, "output": 10.0},
    "grok-3": {"input": 3.0, "output": 15.0},
    "grok-3-mini": {"input": 0.30, "output": 0.50},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING.get(model)
    if rates is None:
        return 0.0
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


class GrokProvider(LLMProvider):
    name = "grok"

    def __init__(
        self,
        api_key: str,
        default_model: str = "grok-3-mini",
        base_url: str = "https://api.x.ai/v1",
    ) -> None:
        if not api_key:
            raise ValueError("XAI_API_KEY / GROK_API_KEY is required for GrokProvider")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role.value}
            if msg.content is not None:
                item["content"] = msg.content
            if msg.tool_calls:
                import json

                item["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.name:
                item["name"] = msg.name
            converted.append(item)
        return converted

    def _convert_tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def _parse_response(self, message: ChatCompletionMessage, usage: Any, model: str) -> LLMResponse:
        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            import json

            for tc in message.tool_calls:
                args: dict[str, Any] = {}
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    logger.warning("failed_to_parse_tool_args", arguments=tc.function.arguments)
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            usage=LLMUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                estimated_cost_usd=_estimate_cost(model, input_tokens, output_tokens),
            ),
            model=model,
            finish_reason=None,
            raw=message,
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
        converted = self._convert_messages(messages)
        openai_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": converted,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools
        if stop:
            kwargs["stop"] = stop

        logger.debug("grok_generate", model=model, tool_count=len(openai_tools or []))
        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        return self._parse_response(choice.message, response.usage, model)

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
        converted = self._convert_messages(messages)

        stream = await self.client.chat.completions.create(
            model=model,
            messages=converted,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def close(self) -> None:
        await self.client.close()
