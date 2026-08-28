"""Agent run execution history and cost tracking."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_APPROVAL = "needs_approval"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    COST_LIMIT = "cost_limit"


class AgentRunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = "default"
    session_id: str = "default"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    model: str = ""
    provider: str = ""
    steps: int = 0
    tools_used: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    approvals: list[str] = Field(default_factory=list)
    tokens: int = 0
    estimated_cost_usd: float = 0.0
    status: RunStatus = RunStatus.RUNNING
    errors: list[str] = Field(default_factory=list)
    input_preview: str = ""
    response_preview: str = ""


class CostLimits(BaseModel):
    max_daily_cost_usd: float = 10.0
    max_monthly_cost_usd: float = 100.0
    max_agent_steps: int = 15
    max_background_tasks: int = 50


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, AgentRunRecord] = {}
        self.limits = CostLimits()

    def start(
        self,
        user_id: str = "default",
        session_id: str = "default",
        input_preview: str = "",
        provider: str = "",
        model: str = "",
    ) -> AgentRunRecord:
        rec = AgentRunRecord(
            user_id=user_id,
            session_id=session_id,
            input_preview=input_preview[:200],
            provider=provider,
            model=model,
        )
        self._runs[rec.run_id] = rec
        return rec

    def finish(
        self,
        run_id: str,
        *,
        status: RunStatus,
        steps: int = 0,
        tools_used: list[str] | None = None,
        tokens: int = 0,
        cost: float = 0.0,
        response_preview: str = "",
        error: str | None = None,
    ) -> AgentRunRecord | None:
        rec = self._runs.get(run_id)
        if not rec:
            return None
        rec.finished_at = datetime.utcnow()
        rec.status = status
        rec.steps = steps
        if tools_used:
            rec.tools_used = tools_used
        rec.tokens = tokens
        rec.estimated_cost_usd = cost
        rec.response_preview = response_preview[:200]
        if error:
            rec.errors.append(error)
        return rec

    def get(self, run_id: str) -> AgentRunRecord | None:
        return self._runs.get(run_id)

    def list_for_user(self, user_id: str = "default", limit: int = 50) -> list[AgentRunRecord]:
        items = [r for r in self._runs.values() if r.user_id == user_id]
        items.sort(key=lambda r: r.started_at, reverse=True)
        return items[:limit]

    def daily_cost(self, user_id: str = "default") -> float:
        today = datetime.utcnow().date()
        return sum(
            r.estimated_cost_usd
            for r in self._runs.values()
            if r.user_id == user_id and r.started_at.date() == today
        )

    def monthly_cost(self, user_id: str = "default") -> float:
        now = datetime.utcnow()
        return sum(
            r.estimated_cost_usd
            for r in self._runs.values()
            if r.user_id == user_id
            and r.started_at.year == now.year
            and r.started_at.month == now.month
        )

    def check_cost_limits(self, user_id: str = "default") -> tuple[bool, str]:
        daily = self.daily_cost(user_id)
        monthly = self.monthly_cost(user_id)
        if daily >= self.limits.max_daily_cost_usd:
            return False, f"Daily cost limit reached ({daily:.4f} >= {self.limits.max_daily_cost_usd})"
        if monthly >= self.limits.max_monthly_cost_usd:
            return (
                False,
                f"Monthly cost limit reached ({monthly:.4f} >= {self.limits.max_monthly_cost_usd})",
            )
        return True, ""


run_store = RunStore()
