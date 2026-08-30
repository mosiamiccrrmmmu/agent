"""Risk policy for Computer Use actions."""

from __future__ import annotations

from app.computer.models import ComputerActionType
from app.tools.base import RiskLevel

ComputerAction = ComputerActionType


class ComputerPolicy:
    max_actions: int = 40
    max_runtime_seconds: float = 180.0
    max_type_length: int = 2000
    max_repeated_clicks: int = 10

    SENSITIVE_TITLE_MARKERS = (
        "password",
        "credential",
        "1password",
        "bitwarden",
        "lastpass",
        "keepass",
        "bank",
        "banking",
        "uac",
        "user account control",
        "credential manager",
    )

    BLOCKED_HOTKEYS = {
        "alt+f4",
        "ctrl+alt+del",
        "win+l",
    }

    def risk_for(
        self,
        action: ComputerActionType,
        *,
        window_title: str = "",
        text: str = "",
    ) -> RiskLevel:
        title = (window_title or "").lower()
        if any(m in title for m in self.SENSITIVE_TITLE_MARKERS):
            return RiskLevel.CRITICAL

        low = {
            ComputerActionType.OBSERVE,
            ComputerActionType.SCREENSHOT,
            ComputerActionType.WINDOW_LIST,
            ComputerActionType.MOVE,
            ComputerActionType.SCROLL,
        }
        medium = {
            ComputerActionType.CLICK,
            ComputerActionType.DOUBLE_CLICK,
            ComputerActionType.RIGHT_CLICK,
            ComputerActionType.DRAG,
            ComputerActionType.TYPE,
            ComputerActionType.PRESS,
            ComputerActionType.FOCUS_WINDOW,
        }
        high = {ComputerActionType.HOTKEY}
        if action in low:
            return RiskLevel.LOW
        if action in medium:
            return RiskLevel.MEDIUM
        if action in high:
            return RiskLevel.HIGH
        return RiskLevel.HIGH

    def requires_approval(
        self,
        action: ComputerActionType,
        *,
        window_title: str = "",
        text: str = "",
    ) -> bool:
        risk = self.risk_for(action, window_title=window_title, text=text)
        return risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def is_hotkey_blocked(self, keys: str) -> bool:
        normalized = keys.lower().replace(" ", "")
        return normalized in self.BLOCKED_HOTKEYS
