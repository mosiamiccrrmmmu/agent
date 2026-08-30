"""Wire plan logging + run persistence around AgentOrchestrator.run."""

from __future__ import annotations

import contextlib
from functools import wraps

from app.agent.lifecycle import AgentLifecycle, AgentState
from app.agent.planner import DeterministicPlanner
from app.core.logging import get_logger

logger = get_logger(__name__)


def install_execution_hooks() -> None:
    from app.agent import orchestrator as orch

    if getattr(orch.AgentOrchestrator.run, "_pai_hooks", False):
        return
    original = orch.AgentOrchestrator.run

    @wraps(original)
    async def run_wrapped(
        self,
        user_message: str,
        *,
        session_id: str = "default",
        user_id: str = "default",
        max_steps: int | None = None,
    ):
        life = AgentLifecycle(AgentState.IDLE)
        _plan = await DeterministicPlanner().create_plan(user_message)
        with contextlib.suppress(Exception):
            life.transition(AgentState.PLANNING)
            life.transition(AgentState.RUNNING)
        _store = None
        with contextlib.suppress(Exception):
            from app.database.sqlite_store import SQLiteStore

            _store = SQLiteStore()
        result = await original(
            self,
            user_message,
            session_id=session_id,
            user_id=user_id,
            max_steps=max_steps,
        )
        if _store is not None:
            with contextlib.suppress(Exception):
                _store.upsert_agent_run(
                    result.run_id,
                    session_id=session_id,
                    user_id=user_id,
                    status=result.status,
                    goal=user_message[:500],
                    plan=_plan.model_dump(),
                    current_step=result.steps,
                    finished=True,
                    error=result.error,
                    started=True,
                )
        return result

    run_wrapped._pai_hooks = True  # type: ignore[attr-defined]
    orch.AgentOrchestrator.run = run_wrapped  # type: ignore[method-assign]
    logger.info("execution_hooks_installed")
