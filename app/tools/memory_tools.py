from __future__ import annotations

"""Tools for reading/writing long-term memory (with proper control)."""

from typing import Any, ClassVar, Type

from pydantic import BaseModel, Field

from app.memory.long_term import LongTermMemory
from app.tools.base import BaseTool, RiskLevel, ToolMetadata, ToolResult

_long_term = LongTermMemory()


class RememberArgs(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    category: str = Field(default="general", min_length=1, max_length=64)


class RecallArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class RememberTool(BaseTool):
    args_model: ClassVar[Type[BaseModel]] = RememberArgs

    metadata = ToolMetadata(
        name="remember",
        description=(
            "Store an important fact about the user for future conversations. "
            "Only use when the user explicitly asks to remember something or "
            "when the information is clearly durable."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The fact to remember",
                    "minLength": 1,
                    "maxLength": 2000,
                },
                "category": {
                    "type": "string",
                    "description": "Category (e.g. preference, contact, work)",
                    "default": "general",
                },
            },
            "required": ["content"],
        },
        risk_level=RiskLevel.MEDIUM,
        tags=["memory"],
    )

    async def execute(
        self, content: str, category: str = "general", **_: Any
    ) -> ToolResult:
        item = _long_term.add(content=content, category=category, source="agent")
        return ToolResult(
            success=True, data={"id": item.id, "content": item.content}
        )


class RecallTool(BaseTool):
    args_model: ClassVar[Type[BaseModel]] = RecallArgs

    metadata = ToolMetadata(
        name="recall",
        description="Search long-term memory for facts about the user.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for",
                    "minLength": 1,
                    "maxLength": 500,
                },
            },
            "required": ["query"],
        },
        risk_level=RiskLevel.LOW,
        tags=["memory"],
    )

    async def execute(self, query: str, **_: Any) -> ToolResult:
        items = _long_term.search(query)
        return ToolResult(
            success=True,
            data=[
                {"id": i.id, "content": i.content, "category": i.category}
                for i in items
            ],
        )
