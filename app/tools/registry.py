from __future__ import annotations

"""Central Tool Registry.

Tools register themselves here so the Agent can discover them at runtime.
All executions go through argument validation before the tool body runs.
"""

from typing import Any

from app.core.logging import get_logger
from app.tools.base import BaseTool, RiskLevel, ToolResult

logger = get_logger(__name__)


class ToolRegistry:
    """Singleton-like registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        name = tool.metadata.name
        if name in self._tools:
            logger.warning("tool_already_registered_overwriting", name=name)
        self._tools[name] = tool
        logger.info(
            "tool_registered",
            name=name,
            risk=tool.metadata.risk_level.value,
        )

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list:
        return [t.metadata for t in self._tools.values()]

    def list_for_llm(self) -> list[dict[str, Any]]:
        return [t.to_llm_definition() for t in self._tools.values()]

    def get_by_risk(self, max_risk: RiskLevel) -> list[BaseTool]:
        order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_idx = order.index(max_risk)
        return [
            t
            for t in self._tools.values()
            if order.index(t.metadata.risk_level) <= max_idx
        ]

    async def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"Tool '{name}' not found")
        try:
            validated = tool.validate_arguments(arguments or {})
        except ValueError as exc:
            logger.warning("tool_validation_failed", tool=name, error=str(exc))
            return ToolResult(success=False, error=f"Invalid arguments: {exc}")
        try:
            return await tool.execute(**validated)
        except Exception as exc:
            logger.exception("tool_execution_failed", tool=name)
            return ToolResult(success=False, error=str(exc))


tool_registry = ToolRegistry()
