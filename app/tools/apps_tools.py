"""Allowlisted application tools."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.apps.manager import application_manager
from app.tools.base import BaseTool, RiskLevel, ToolMetadata, ToolResult


class LaunchAppArgs(BaseModel):
    app_id: str = Field(..., min_length=1, max_length=64)


class ListAppsArgs(BaseModel):
    pass


class ListAppsTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = ListAppsArgs
    metadata = ToolMetadata(
        name="list_apps",
        description="List allowlisted applications that can be launched.",
        input_schema={"type": "object", "properties": {}},
        risk_level=RiskLevel.LOW,
        tags=["apps"],
    )

    async def execute(self, **_: Any) -> ToolResult:
        return ToolResult(success=True, data={"apps": application_manager.list_apps()})


class LaunchAppTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = LaunchAppArgs
    metadata = ToolMetadata(
        name="launch_app",
        description="Launch an allowlisted application (Notepad, Calculator, Chrome, Edge, Explorer).",
        input_schema={
            "type": "object",
            "properties": {"app_id": {"type": "string"}},
            "required": ["app_id"],
        },
        risk_level=RiskLevel.MEDIUM,
        tags=["apps"],
    )

    async def execute(self, app_id: str, **_: Any) -> ToolResult:
        result = application_manager.launch(app_id)
        return ToolResult(
            success=bool(result.get("success")),
            data=result.get("data"),
            error=result.get("error"),
        )
