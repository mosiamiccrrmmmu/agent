"""Browser agent tools."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.browser.session import BrowserSession
from app.tools.base import BaseTool, RiskLevel, ToolMetadata, ToolResult

_session: BrowserSession | None = None


async def _get_session() -> BrowserSession:
    global _session
    if _session is None:
        _session = BrowserSession()
        await _session.start()
    return _session


class NavigateArgs(BaseModel):
    url: str = Field(..., min_length=3, max_length=2000)


class EmptyArgs(BaseModel):
    pass


class NavigateTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = NavigateArgs
    metadata = ToolMetadata(
        name="browser_navigate",
        description="Open a URL in the isolated browser session.",
        input_schema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        risk_level=RiskLevel.LOW,
        tags=["browser"],
    )

    async def execute(self, url: str, **_: Any) -> ToolResult:
        session = await _get_session()
        result = await session.navigate(url)
        return ToolResult(
            success=result.get("success", False), data=result, error=result.get("error")
        )


class ExtractTextTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = EmptyArgs
    metadata = ToolMetadata(
        name="browser_extract_text",
        description="Extract visible text from the current browser page.",
        input_schema={"type": "object", "properties": {}},
        risk_level=RiskLevel.LOW,
        tags=["browser"],
    )

    async def execute(self, **_: Any) -> ToolResult:
        session = await _get_session()
        result = await session.extract_text()
        return ToolResult(success=True, data=result)
