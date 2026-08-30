"""Computer driver abstraction — Agent Core never talks to OS APIs directly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.computer.models import ActionResult, ComputerActionType, Observation


class ComputerDriver(ABC):
    """Platform-specific implementation of desktop control."""

    name: str = "base"

    @abstractmethod
    async def observe(self) -> Observation:
        ...

    @abstractmethod
    async def screenshot(self) -> Observation:
        ...

    @abstractmethod
    async def window_list(self) -> Observation:
        ...

    @abstractmethod
    async def focus_window(self, title_contains: str) -> ActionResult:
        ...

    @abstractmethod
    async def move(self, x: int, y: int) -> ActionResult:
        ...

    @abstractmethod
    async def click(self, x: int, y: int, button: str = "left") -> ActionResult:
        ...

    @abstractmethod
    async def double_click(self, x: int, y: int) -> ActionResult:
        ...

    @abstractmethod
    async def right_click(self, x: int, y: int) -> ActionResult:
        ...

    @abstractmethod
    async def drag(self, x1: int, y1: int, x2: int, y2: int) -> ActionResult:
        ...

    @abstractmethod
    async def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> ActionResult:
        ...

    @abstractmethod
    async def type_text(self, text: str) -> ActionResult:
        ...

    @abstractmethod
    async def press(self, key: str) -> ActionResult:
        ...

    @abstractmethod
    async def hotkey(self, keys: list[str]) -> ActionResult:
        ...

    async def execute(self, action: ComputerActionType, params: dict[str, Any]) -> ActionResult:
        if action == ComputerActionType.OBSERVE:
            obs = await self.observe()
            return ActionResult(success=True, observation=obs)
        if action == ComputerActionType.SCREENSHOT:
            obs = await self.screenshot()
            return ActionResult(success=True, observation=obs)
        if action == ComputerActionType.WINDOW_LIST:
            obs = await self.window_list()
            return ActionResult(success=True, observation=obs)
        if action == ComputerActionType.FOCUS_WINDOW:
            return await self.focus_window(str(params.get("title_contains", "")))
        if action == ComputerActionType.MOVE:
            return await self.move(int(params["x"]), int(params["y"]))
        if action == ComputerActionType.CLICK:
            return await self.click(
                int(params["x"]), int(params["y"]), str(params.get("button", "left"))
            )
        if action == ComputerActionType.DOUBLE_CLICK:
            return await self.double_click(int(params["x"]), int(params["y"]))
        if action == ComputerActionType.RIGHT_CLICK:
            return await self.right_click(int(params["x"]), int(params["y"]))
        if action == ComputerActionType.DRAG:
            return await self.drag(
                int(params["x1"]), int(params["y1"]), int(params["x2"]), int(params["y2"])
            )
        if action == ComputerActionType.SCROLL:
            return await self.scroll(
                int(params.get("clicks", 1)),
                int(params["x"]) if params.get("x") is not None else None,
                int(params["y"]) if params.get("y") is not None else None,
            )
        if action == ComputerActionType.TYPE:
            return await self.type_text(str(params.get("text", "")))
        if action == ComputerActionType.PRESS:
            return await self.press(str(params.get("key", "")))
        if action == ComputerActionType.HOTKEY:
            return await self.hotkey(list(params.get("keys") or []))
        return ActionResult(success=False, error=f"Unsupported action: {action}")
