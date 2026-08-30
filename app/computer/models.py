"""Computer Use models and action types."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ComputerActionType(StrEnum):
    OBSERVE = "observe"
    SCREENSHOT = "screenshot"
    WINDOW_LIST = "window_list"
    FOCUS_WINDOW = "focus_window"
    MOVE = "move"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    SCROLL = "scroll"
    TYPE = "type"
    PRESS = "press"
    HOTKEY = "hotkey"


class UIElement(BaseModel):
    name: str = ""
    control_type: str = ""
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    automation_id: str | None = None


class Observation(BaseModel):
    screenshot_b64: str | None = None
    text: str = ""
    screen_width: int | None = None
    screen_height: int | None = None
    active_window_title: str | None = None
    windows: list[str] = Field(default_factory=list)
    elements: list[UIElement] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    simulated: bool = False


class ActionResult(BaseModel):
    success: bool
    observation: Observation = Field(default_factory=Observation)
    error: str | None = None
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    duration_ms: float = 0.0


class ComputerAuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    run_id: str
    action: str
    target: str = ""
    application: str = ""
    risk: str = ""
    approval_id: str | None = None
    result: str = ""
    duration_ms: float = 0.0


class ComputerSessionState(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    action_count: int = 0
    start_time: datetime = Field(default_factory=datetime.utcnow)
    cancelled: bool = False
    timed_out: bool = False


ALLOWED_KEYS = frozenset(
    {
        "enter", "tab", "escape", "esc", "backspace", "delete", "space",
        "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
        "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
        "ctrl", "alt", "shift", "win", "cmd",
    }
)


class ComputerActionRequest(BaseModel):
    action: ComputerActionType
    x: int | None = None
    y: int | None = None
    x1: int | None = None
    y1: int | None = None
    x2: int | None = None
    y2: int | None = None
    button: str = "left"
    clicks: int = 1
    text: str | None = None
    key: str | None = None
    keys: list[str] | None = None
    title_contains: str | None = None

    @field_validator("x", "y", "x1", "y1", "x2", "y2")
    @classmethod
    def non_negative_coords(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("coordinates must be >= 0")
        return v

    @field_validator("text")
    @classmethod
    def text_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 2000:
            raise ValueError("text too long (max 2000)")
        return v

    @field_validator("clicks")
    @classmethod
    def scroll_limit(cls, v: int) -> int:
        if abs(v) > 50:
            raise ValueError("scroll clicks max 50")
        return v

    @field_validator("key")
    @classmethod
    def valid_key(cls, v: str | None) -> str | None:
        if v is None:
            return v
        low = v.lower()
        if low not in ALLOWED_KEYS and len(low) != 1:
            raise ValueError(f"unsupported key: {v}")
        return v

    def to_params(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if k != "action" and v is not None}
