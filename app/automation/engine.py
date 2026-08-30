"""No-AI automation: sequential workflow steps with policy gates."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agent.cancel import is_agent_cancelled
from app.core.execution_gate import is_blocked
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class WorkflowStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    error: str | None = None


class Workflow(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    steps: list[WorkflowStep] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AutomationEngine:
    """Execute deterministic workflows without LLM."""

    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}

    def create(self, name: str, steps: list[dict[str, Any]]) -> Workflow:
        wf = Workflow(
            name=name,
            steps=[
                WorkflowStep(action=s["action"], arguments=s.get("arguments") or {})
                for s in steps
            ],
            status=WorkflowStatus.ACTIVE,
        )
        self._workflows[wf.workflow_id] = wf
        return wf

    def get(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    async def run(self, workflow_id: str, executor) -> Workflow:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise KeyError(workflow_id)
        if is_blocked():
            wf.status = WorkflowStatus.CANCELLED
            return wf
        wf.status = WorkflowStatus.RUNNING
        for step in wf.steps:
            if is_blocked() or is_agent_cancelled():
                step.status = StepStatus.CANCELLED
                wf.status = WorkflowStatus.CANCELLED
                for rest in wf.steps:
                    if rest.status == StepStatus.PENDING:
                        rest.status = StepStatus.SKIPPED
                return wf
            step.status = StepStatus.RUNNING
            try:
                result = await executor(step.action, step.arguments)
            except Exception as exc:
                step.status = StepStatus.FAILED
                step.error = str(exc)
                wf.status = WorkflowStatus.FAILED
                return wf
            if not result.get("success", False):
                step.status = StepStatus.FAILED
                step.error = str(result.get("error") or result.get("status") or "FAILED")
                wf.status = WorkflowStatus.FAILED
                return wf
            step.status = StepStatus.SUCCEEDED
        wf.status = WorkflowStatus.COMPLETED
        return wf


automation_engine = AutomationEngine()
