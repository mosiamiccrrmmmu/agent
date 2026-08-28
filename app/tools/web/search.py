from __future__ import annotations

"""Web search tool (MVP placeholder — no live network dependency for tests)."""

from typing import Any, ClassVar, Type

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, RiskLevel, ToolMetadata, ToolResult


class WebSearchArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)


class WebSearchTool(BaseTool):
    args_model: ClassVar[Type[BaseModel]] = WebSearchArgs

    metadata = ToolMetadata(
        name="search_web",
        description=(
            "Search the web for information. Use when you need up-to-date "
            "or external knowledge."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                    "minLength": 1,
                    "maxLength": 500,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default 5)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["query"],
        },
        risk_level=RiskLevel.LOW,
        tags=["web", "search"],
    )

    async def execute(
        self, query: str, max_results: int = 5, **_: Any
    ) -> ToolResult:
        results = [
            {
                "title": f"Search results for: {query}",
                "snippet": (
                    "Web search completed (MVP placeholder). "
                    "Replace with Serper/Tavily/Brave for live results."
                ),
                "url": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
            }
        ]
        return ToolResult(
            success=True,
            data={
                "query": query,
                "results": results[:max_results],
                "note": "MVP placeholder — no live network call.",
            },
        )
