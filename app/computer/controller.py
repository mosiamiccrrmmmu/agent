"""Computer Use controller — observation/action loop abstraction.

This does NOT grant unrestricted desktop control. Real OS drivers are
pluggable; the default is a safe no-op simulator for tests.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.computer.policy import ComputerAction, ComputerPolicy
from app.core.logging import get_logger

logger = get_logger(__name__)


class Observation(BaseModel):
    screenshot_b64: str | None = None
    text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    success: bool
    observation: Observation = Field(default_factory=Observation)
    error: str | None = None
    action_id: str = Field(default_factory=lambda: str(uuid4()))


class ComputerController:
    def __init__(self, policy: ComputerPolicy | None = None) -> None:
        self.policy = policy or ComputerPolicy()
        self._action_count = 0
        self._session_id = str(uuid4())

    def reset(self) -> None:
        self._action_count = 0
        self._session_id = str(uuid4())

    async def act(
        self,
        action: ComputerAction,
        *,
        approved: bool = False,
        **params: Any,
    ) -> ActionResult:
        if self._action_count >= self.policy.max_actions:
            return ActionResult(
                success=False,
                error=f"max_actions ({self.policy.max_actions}) reached — stopping to avoid loops",
            )

        if self.policy.requires_approval(action) and not approved:
            return ActionResult(
                success=False,
                error=f"Action {action.value} requires human approval",
            )

        if action == ComputerAction.HOTKEY and self.policy.is_hotkey_blocked(
            str(params.get("keys", ""))
        ):
            return ActionResult(success=False, error="Hotkey blocked by ComputerPolicy")

        self._action_count += 1
        logger.info(
            "computer_action",
            session=self._session_id,
            action=action.value,
            count=self._action_count,
        )

        # Safe simulator — real backends (Playwright desktop, OS APIs) plug in here
        return ActionResult(
            success=True,
            observation=Observation(
                text=f"Simulated {action.value} with {params}",
                metadata={"simulated": True, "action_count": self._action_count},
            ),
        )

    async def screenshot(self) -> ActionResult:
        return await self.act(ComputerAction.SCREENSHOT)
