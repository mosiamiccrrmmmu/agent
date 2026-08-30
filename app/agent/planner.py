"""Formal planner abstraction — LLM may propose; code owns structure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PlanStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk: str = "low"
    timeout_seconds: float = 30.0
    depends_on: list[str] = Field(default_factory=list)
    status: PlanStepStatus = PlanStepStatus.PENDING
    result_preview: str | None = None


class Plan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)
    notes: str = ""


class Planner(ABC):
    @abstractmethod
    async def create_plan(self, user_message: str, *, context: str = "") -> Plan:
        ...


class DeterministicPlanner(Planner):
    """Heuristic plan without LLM — useful offline / no-AI mode."""

    async def create_plan(self, user_message: str, *, context: str = "") -> Plan:
        msg = user_message.lower()
        steps: list[PlanStep] = []
        if any(w in msg for w in ("search", "جستجو", "web", "google")):
            steps.append(
                PlanStep(
                    description="Search the web",
                    tool="search_web",
                    arguments={"query": user_message[:200]},
                    risk="low",
                )
            )
        if any(w in msg for w in ("remember", "یاد", "memor")):
            steps.append(
                PlanStep(
                    description="Store in long-term memory",
                    tool="remember",
                    arguments={"content": user_message[:500]},
                    risk="medium",
                )
            )
        if any(w in msg for w in ("notepad", "نوت‌پد", "launch", "باز کن", "open")):
            app_id = "notepad"
            if "chrome" in msg or "کروم" in msg:
                app_id = "chrome"
            elif "calc" in msg or "ماشین" in msg:
                app_id = "calculator"
            steps.append(
                PlanStep(
                    description=f"Launch application {app_id}",
                    tool="launch_app",
                    arguments={"app_id": app_id},
                    risk="medium",
                )
            )
        if any(w in msg for w in ("file", "فایل", "list", "لیست")):
            steps.append(
                PlanStep(
                    description="List sandbox files",
                    tool="list_files",
                    arguments={"path": "."},
                    risk="low",
                )
            )
        if not steps:
            steps.append(
                PlanStep(
                    description="Respond via LLM / conversation",
                    tool=None,
                    risk="low",
                )
            )
        return Plan(goal=user_message[:500], steps=steps)


class MockPlanner(DeterministicPlanner):
    """Alias for tests."""


class LLMPlanner(Planner):
    """Uses deterministic plan as base; LLM can refine later."""

    def __init__(self, fallback: Planner | None = None) -> None:
        self.fallback = fallback or DeterministicPlanner()

    async def create_plan(self, user_message: str, *, context: str = "") -> Plan:
        return await self.fallback.create_plan(user_message, context=context)
