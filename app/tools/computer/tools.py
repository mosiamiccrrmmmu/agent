"""Computer Use tools — policy gated."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.computer.controller import ComputerController
from app.computer.policy import ComputerAction
from app.tools.base import BaseTool, RiskLevel, ToolMetadata, ToolResult

_controller = ComputerController()


class ComputerActionArgs(BaseModel):
    action: str = Field(..., description="screenshot|scroll|click|type|hotkey|wait")
    params: dict[str, Any] = Field(default_factory=dict)


class ComputerActTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = ComputerActionArgs
    metadata = ToolMetadata(
        name="computer_act",
        description=(
            "Perform a computer-use action (screenshot, click, type, ...). "
            "HIGH-risk actions require approval."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "params": {"type": "object"},
            },
            "required": ["action"],
        },
        risk_level=RiskLevel.MEDIUM,
        tags=["computer"],
    )

    async def execute(self, action: str, params: dict[str, Any] | None = None, **_: Any) -> ToolResult:
        try:
            act = ComputerAction(action)
        except ValueError:
            return ToolResult(success=False, error=f"Unknown action: {action}")
        risk = _controller.policy.risk_for(act)
        if _controller.policy.requires_approval(act):
            return ToolResult(
                success=False,
                error=f"Action {action} requires approval (risk={risk.value})",
            )
        result = await _controller.act(act, **(params or {}))
        return ToolResult(success=result.success, data=result.model_dump(), error=result.error)
