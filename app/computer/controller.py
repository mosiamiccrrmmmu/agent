"""Computer Use controller — session limits, emergency stop, audit, driver dispatch."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from app.computer.base import ComputerDriver
from app.computer.models import (
    ActionResult,
    ComputerActionRequest,
    ComputerActionType,
    ComputerAuditEntry,
    ComputerSessionState,
    Observation,
)
from app.computer.policy import ComputerPolicy
from app.core.logging import get_logger

logger = get_logger(__name__)

_EMERGENCY_STOP = False


def trigger_emergency_stop() -> None:
    global _EMERGENCY_STOP
    _EMERGENCY_STOP = True
    logger.warning("computer_emergency_stop")


def clear_emergency_stop() -> None:
    global _EMERGENCY_STOP
    _EMERGENCY_STOP = False


def is_emergency_stopped() -> bool:
    return _EMERGENCY_STOP


class ComputerController:
    def __init__(
        self,
        driver: ComputerDriver,
        policy: ComputerPolicy | None = None,
    ) -> None:
        self.driver = driver
        self.policy = policy or ComputerPolicy()
        self.state = ComputerSessionState()
        self.audit: list[ComputerAuditEntry] = []

    def reset(self) -> None:
        self.state = ComputerSessionState()
        clear_emergency_stop()

    def cancel(self) -> None:
        self.state.cancelled = True
        trigger_emergency_stop()

    async def act(
        self,
        action: ComputerActionType | str,
        *,
        approved: bool = False,
        approval_id: str | None = None,
        window_title: str = "",
        **params: Any,
    ) -> ActionResult:
        if isinstance(action, str):
            try:
                action = ComputerActionType(action)
            except ValueError:
                return ActionResult(success=False, error=f"Unknown action: {action}")

        if is_emergency_stopped() or self.state.cancelled:
            return ActionResult(success=False, error="Computer Use cancelled (emergency stop)")

        elapsed = (datetime.utcnow() - self.state.start_time).total_seconds()
        if elapsed > self.policy.max_runtime_seconds:
            self.state.timed_out = True
            return ActionResult(
                success=False,
                error=f"Computer Use timeout ({self.policy.max_runtime_seconds}s)",
            )

        if self.state.action_count >= self.policy.max_actions:
            return ActionResult(
                success=False,
                error=f"max_actions ({self.policy.max_actions}) reached",
            )

        try:
            req = ComputerActionRequest(action=action, **params)
            params = req.to_params()
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid arguments: {exc}")

        text = str(params.get("text", "") or "")
        risk = self.policy.risk_for(action, window_title=window_title, text=text)
        if self.policy.requires_approval(action, window_title=window_title, text=text) and not approved:
            return ActionResult(
                success=False,
                error=f"Action {action.value} requires human approval (risk={risk.value})",
            )

        if action == ComputerActionType.HOTKEY:
            keys = params.get("keys") or []
            key_str = "+".join(str(k) for k in keys)
            if self.policy.is_hotkey_blocked(key_str):
                return ActionResult(success=False, error="Hotkey blocked by ComputerPolicy")

        if action == ComputerActionType.TYPE and len(text) > self.policy.max_type_length:
            return ActionResult(success=False, error="Type text exceeds max length")

        self.state.action_count += 1
        t0 = time.perf_counter()
        result = await self.driver.execute(action, params)
        duration = (time.perf_counter() - t0) * 1000
        result.duration_ms = duration

        target = ""
        if "x" in params and "y" in params:
            target = f"{params.get('x')},{params.get('y')}"
        elif text:
            target = f"text_len={len(text)}"
        entry = ComputerAuditEntry(
            run_id=self.state.run_id,
            action=action.value,
            target=target,
            application=window_title or (result.observation.active_window_title or ""),
            risk=risk.value,
            approval_id=approval_id,
            result="ok" if result.success else (result.error or "error"),
            duration_ms=duration,
        )
        self.audit.append(entry)
        logger.info(
            "computer_action",
            run_id=self.state.run_id,
            action=action.value,
            count=self.state.action_count,
            success=result.success,
            driver=self.driver.name,
        )
        return result

    async def observe(self) -> Observation:
        return await self.driver.observe()
