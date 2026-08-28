from __future__ import annotations

"""LLM Provider abstraction.

All providers implement this interface so the Agent Core remains
provider-agnostic.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """A tool call requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """Standard chat message."""

    role: MessageRole
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # for tool results


class LLMUsage(BaseModel):
    """Token usage for a single generation."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: LLMUsage = Field(default_factory=LLMUsage)
    model: str = ""
    finish_reason: str | None = None
    raw: Any = None  # original provider response if needed


class ToolDefinition(BaseModel):
    """Tool schema passed to the LLM."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    name: str

    @abstractmethod
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
        """Generate a completion (non-streaming)."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream text tokens. Tool calls are not supported in stream mode for MVP."""
        ...

    async def close(self) -> None:
        """Cleanup resources (optional)."""
        pass
