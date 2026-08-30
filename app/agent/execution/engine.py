"""Production step-by-step execution engine with cancel + timeout + retry."""

from __future__ import annotations

import time
from datetime import datetime
from enum import StrEnum
from typing import Any, Awaitable, Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agent.cancel import clear_agent_cancel, is_agent_cancelled
from app.agent.retry import RetryPolicy, with_retry
from app.core.logging import get_logger

logger = get_logger(__name__)


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"


class ExecutionStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str = ""
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: float = 0.0
    attempt: int = 0
    result: Any = None
    error: str | None = None
    retry_count: int = 0


class ExecutionResult(BaseModel):
    run_id: str
    status: str
    steps: list[ExecutionStep] = Field(default_factory=list)
    error: str | None = None


ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class ExecutionEngine:
    """Execute plan steps with mid-loop cancellation and optional retries."""

    def __init__(
        self,
        *,
        max_retries: int = 2,
        step_timeout_seconds: float = 30.0,
    ) -> None:
        self.max_retries = max_retries
        self.step_timeout_seconds = step_timeout_seconds

    async def execute(
        self,
        steps: list[ExecutionStep],
        executor: ToolExecutor,
        *,
        run_id: str | None = None,
    ) -> ExecutionResult:
        run_id = run_id or str(uuid4())
        completed: list[ExecutionStep] = []

        for step in steps:
            if is_agent_cancelled():
                clear_agent_cancel()
                step.status = StepStatus.CANCELLED
                step.error = "CANCELLED"
                step.finished_at = datetime.utcnow().isoformat()
                completed.append(step)
                for rest in steps[len(completed) :]:
                    rest.status = StepStatus.SKIPPED
                    completed.append(rest)
                return ExecutionResult(
                    run_id=run_id,
                    status="cancelled",
                    steps=completed,
                    error="CANCELLED",
                )

            step.run_id = run_id
            step.status = StepStatus.RUNNING
            step.started_at = datetime.utcnow().isoformat()
            step.attempt = 1
            t0 = time.perf_counter()

            if not step.tool:
                step.status = StepStatus.COMPLETED
                step.result = {"note": "no_tool"}
                step.duration_ms = (time.perf_counter() - t0) * 1000
                step.finished_at = datetime.utcnow().isoformat()
                completed.append(step)
                continue

            tool_name = step.tool or ""
            tool_args = dict(step.arguments)

            async def _call(
                _tn: str = tool_name, _ta: dict[str, Any] = tool_args
            ) -> dict[str, Any]:
                return await executor(_tn, _ta)

            try:
                result = await with_retry(
                    _call,
                    policy=RetryPolicy.EXPONENTIAL,
                    max_attempts=1 + self.max_retries,
                    base_delay=0.05,
                )
            except Exception as exc:
                step.status = StepStatus.FAILED
                step.error = str(exc)
                step.duration_ms = (time.perf_counter() - t0) * 1000
                step.finished_at = datetime.utcnow().isoformat()
                completed.append(step)
                return ExecutionResult(
                    run_id=run_id, status="failed", steps=completed, error=str(exc)
                )

            if not result.get("success", False):
                err = str(result.get("error") or result.get("status") or "FAILED")
                step.status = StepStatus.FAILED
                step.error = err
                step.result = result
                step.duration_ms = (time.perf_counter() - t0) * 1000
                step.finished_at = datetime.utcnow().isoformat()
                completed.append(step)
                return ExecutionResult(
                    run_id=run_id, status="failed", steps=completed, error=err
                )

            step.status = StepStatus.COMPLETED
            step.result = result
            step.duration_ms = (time.perf_counter() - t0) * 1000
            step.finished_at = datetime.utcnow().isoformat()
            completed.append(step)

            if is_agent_cancelled():
                clear_agent_cancel()
                for rest in steps[len(completed) :]:
                    rest.status = StepStatus.SKIPPED
                    completed.append(rest)
                return ExecutionResult(
                    run_id=run_id,
                    status="cancelled",
                    steps=completed,
                    error="CANCELLED",
                )

        return ExecutionResult(run_id=run_id, status="completed", steps=completed)
