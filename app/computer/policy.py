"""Computer Use security policy.

HIGH and CRITICAL actions require explicit user approval.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.tools.base import RiskLevel


class ComputerAction(StrEnum):
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    TYPE = "type"
    HOTKEY = "hotkey"
    WAIT = "wait"
    OPEN_APP = "open_app"
    NAVIGATE = "navigate"


ACTION_RISK: dict[ComputerAction, RiskLevel] = {
    ComputerAction.SCREENSHOT: RiskLevel.LOW,
    ComputerAction.SCROLL: RiskLevel.LOW,
    ComputerAction.WAIT: RiskLevel.LOW,
    ComputerAction.NAVIGATE: RiskLevel.LOW,
    ComputerAction.CLICK: RiskLevel.MEDIUM,
    ComputerAction.TYPE: RiskLevel.MEDIUM,
    ComputerAction.DOUBLE_CLICK: RiskLevel.MEDIUM,
    ComputerAction.HOTKEY: RiskLevel.HIGH,
    ComputerAction.OPEN_APP: RiskLevel.HIGH,
}


class ComputerPolicy(BaseModel):
    max_actions: int = 30
    timeout_seconds: int = 120
    max_retries: int = 2
    allow_high_without_approval: bool = False
    blocked_hotkeys: list[str] = Field(
        default_factory=lambda: ["ctrl+shift+delete", "alt+f4", "cmd+q"]
    )

    def risk_for(self, action: ComputerAction) -> RiskLevel:
        return ACTION_RISK.get(action, RiskLevel.HIGH)

    def requires_approval(self, action: ComputerAction) -> bool:
        risk = self.risk_for(action)
        if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return not self.allow_high_without_approval
        return False

    def is_hotkey_blocked(self, hotkey: str) -> bool:
        normalized = hotkey.lower().replace(" ", "")
        return normalized in {h.lower().replace(" ", "") for h in self.blocked_hotkeys}
