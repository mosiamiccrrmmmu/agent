"""MockComputerDriver — deterministic, no real OS control. Used in CI/Linux."""

from __future__ import annotations

from app.computer.base import ComputerDriver
from app.computer.models import ActionResult, Observation, UIElement


class MockComputerDriver(ComputerDriver):
    name = "mock"

    def __init__(self) -> None:
        self._cursor = (0, 0)
        self._typed: list[str] = []
        self._focused = "Mock Notepad"
        self._windows = ["Mock Notepad", "Mock Calculator"]

    async def observe(self) -> Observation:
        return Observation(
            text=f"Mock observe focused={self._focused} cursor={self._cursor}",
            screen_width=1920,
            screen_height=1080,
            active_window_title=self._focused,
            windows=list(self._windows),
            elements=[
                UIElement(name="File", control_type="MenuItem", x=10, y=10),
                UIElement(name="Edit", control_type="MenuItem", x=50, y=10),
            ],
            simulated=True,
            metadata={"driver": "mock"},
        )

    async def screenshot(self) -> Observation:
        obs = await self.observe()
        obs.text = "Mock screenshot (no pixels)"
        obs.metadata["screenshot"] = "mock"
        return obs

    async def window_list(self) -> Observation:
        return Observation(
            text="\n".join(self._windows),
            windows=list(self._windows),
            active_window_title=self._focused,
            simulated=True,
        )

    async def focus_window(self, title_contains: str) -> ActionResult:
        for w in self._windows:
            if title_contains.lower() in w.lower():
                self._focused = w
                return ActionResult(
                    success=True,
                    observation=Observation(
                        active_window_title=w, text=f"Focused {w}", simulated=True
                    ),
                )
        return ActionResult(success=False, error=f"No window matching: {title_contains}")

    async def move(self, x: int, y: int) -> ActionResult:
        self._cursor = (x, y)
        return ActionResult(
            success=True,
            observation=Observation(text=f"Moved to {x},{y}", simulated=True),
        )

    async def click(self, x: int, y: int, button: str = "left") -> ActionResult:
        self._cursor = (x, y)
        return ActionResult(
            success=True,
            observation=Observation(text=f"{button} click at {x},{y}", simulated=True),
        )

    async def double_click(self, x: int, y: int) -> ActionResult:
        return await self.click(x, y)

    async def right_click(self, x: int, y: int) -> ActionResult:
        return await self.click(x, y, button="right")

    async def drag(self, x1: int, y1: int, x2: int, y2: int) -> ActionResult:
        self._cursor = (x2, y2)
        return ActionResult(
            success=True,
            observation=Observation(text=f"Drag {x1},{y1}->{x2},{y2}", simulated=True),
        )

    async def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> ActionResult:
        return ActionResult(
            success=True,
            observation=Observation(text=f"Scroll {clicks}", simulated=True),
        )

    async def type_text(self, text: str) -> ActionResult:
        self._typed.append(text)
        return ActionResult(
            success=True,
            observation=Observation(
                text=f"Typed {len(text)} chars",
                simulated=True,
                metadata={"typed_len": len(text)},
            ),
        )

    async def press(self, key: str) -> ActionResult:
        return ActionResult(
            success=True,
            observation=Observation(text=f"Pressed {key}", simulated=True),
        )

    async def hotkey(self, keys: list[str]) -> ActionResult:
        return ActionResult(
            success=True,
            observation=Observation(text=f"Hotkey {'+'.join(keys)}", simulated=True),
        )
