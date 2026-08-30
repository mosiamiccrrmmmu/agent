"""WindowsComputerDriver — real desktop control on Windows only."""

from __future__ import annotations

import platform
import sys
from typing import Any

from app.computer.base import ComputerDriver
from app.computer.models import ActionResult, Observation, UIElement
from app.core.logging import get_logger

logger = get_logger(__name__)


class WindowsComputerDriver(ComputerDriver):
    name = "windows"

    def __init__(self) -> None:
        if not sys.platform.startswith("win"):
            raise RuntimeError(
                "WindowsComputerDriver only runs on Windows. Use MockComputerDriver on Linux/CI."
            )
        try:
            import pyautogui  # type: ignore

            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            self._pg = pyautogui
        except ImportError as exc:
            raise RuntimeError(
                "pyautogui required. pip install 'personal-ai-agent[computer]'"
            ) from exc
        self._win32: Any = None
        try:
            import win32gui  # type: ignore

            self._win32 = win32gui
        except ImportError:
            logger.warning("pywin32 not available — window enumeration limited")

    async def observe(self) -> Observation:
        w, h = self._pg.size()
        title = self._active_title()
        windows = self._enum_windows()
        return Observation(
            text=f"Windows observe {w}x{h} active={title}",
            screen_width=w,
            screen_height=h,
            active_window_title=title,
            windows=windows,
            elements=[],
            simulated=False,
            metadata={"driver": "windows", "platform": platform.platform()},
        )

    async def screenshot(self) -> Observation:
        obs = await self.observe()
        try:
            img = self._pg.screenshot()
            obs.metadata["screenshot_captured"] = True
            obs.metadata["screenshot_size"] = f"{img.width}x{img.height}"
            obs.text = f"Screenshot captured {img.width}x{img.height}"
        except Exception as exc:
            return Observation(text=f"Screenshot failed: {exc}", simulated=False)
        return obs

    async def window_list(self) -> Observation:
        wins = self._enum_windows()
        return Observation(
            text="\n".join(wins) if wins else "No windows",
            windows=wins,
            active_window_title=self._active_title(),
            simulated=False,
        )

    async def focus_window(self, title_contains: str) -> ActionResult:
        if not self._win32:
            return ActionResult(success=False, error="pywin32 required for focus_window")
        target = None

        def _enum(hwnd, _):  # noqa: ANN001
            nonlocal target
            if self._win32.IsWindowVisible(hwnd):
                t = self._win32.GetWindowText(hwnd)
                if t and title_contains.lower() in t.lower():
                    target = hwnd

        self._win32.EnumWindows(_enum, None)
        if not target:
            return ActionResult(success=False, error=f"Window not found: {title_contains}")
        try:
            self._win32.SetForegroundWindow(target)
            return ActionResult(
                success=True,
                observation=Observation(
                    active_window_title=self._win32.GetWindowText(target),
                    simulated=False,
                ),
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def move(self, x: int, y: int) -> ActionResult:
        self._pg.moveTo(x, y)
        return ActionResult(
            success=True, observation=Observation(text=f"Moved to {x},{y}", simulated=False)
        )

    async def click(self, x: int, y: int, button: str = "left") -> ActionResult:
        self._pg.click(x, y, button=button)
        return ActionResult(
            success=True,
            observation=Observation(text=f"Clicked {button} at {x},{y}", simulated=False),
        )

    async def double_click(self, x: int, y: int) -> ActionResult:
        self._pg.doubleClick(x, y)
        return ActionResult(
            success=True,
            observation=Observation(text=f"Double-click at {x},{y}", simulated=False),
        )

    async def right_click(self, x: int, y: int) -> ActionResult:
        self._pg.rightClick(x, y)
        return ActionResult(
            success=True,
            observation=Observation(text=f"Right-click at {x},{y}", simulated=False),
        )

    async def drag(self, x1: int, y1: int, x2: int, y2: int) -> ActionResult:
        self._pg.moveTo(x1, y1)
        self._pg.dragTo(x2, y2, duration=0.2)
        return ActionResult(
            success=True,
            observation=Observation(text=f"Drag {x1},{y1}->{x2},{y2}", simulated=False),
        )

    async def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> ActionResult:
        if x is not None and y is not None:
            self._pg.moveTo(x, y)
        self._pg.scroll(clicks)
        return ActionResult(
            success=True, observation=Observation(text=f"Scroll {clicks}", simulated=False)
        )

    async def type_text(self, text: str) -> ActionResult:
        self._pg.write(text, interval=0.02)
        return ActionResult(
            success=True,
            observation=Observation(
                text=f"Typed {len(text)} chars",
                simulated=False,
                metadata={"typed_len": len(text)},
            ),
        )

    async def press(self, key: str) -> ActionResult:
        self._pg.press(key)
        return ActionResult(
            success=True, observation=Observation(text=f"Pressed {key}", simulated=False)
        )

    async def hotkey(self, keys: list[str]) -> ActionResult:
        self._pg.hotkey(*keys)
        return ActionResult(
            success=True,
            observation=Observation(text=f"Hotkey {'+'.join(keys)}", simulated=False),
        )

    def _active_title(self) -> str:
        if not self._win32:
            return ""
        try:
            hwnd = self._win32.GetForegroundWindow()
            return self._win32.GetWindowText(hwnd) or ""
        except Exception:
            return ""

    def _enum_windows(self) -> list[str]:
        if not self._win32:
            return []
        titles: list[str] = []

        def _enum(hwnd, _):  # noqa: ANN001
            if self._win32.IsWindowVisible(hwnd):
                t = self._win32.GetWindowText(hwnd)
                if t and t.strip():
                    titles.append(t)

        try:
            self._win32.EnumWindows(_enum, None)
        except Exception:
            return []
        return titles[:50]
