from __future__ import annotations

"""API routes — Phase 1 + Phase 2."""

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.agent.orchestrator import AgentOrchestrator, AgentRunResult
from app.config import get_settings
from app.core.logging import get_logger
from app.permissions.manager import permission_manager
from app.tools.registry import tool_registry

logger = get_logger(__name__)
router = APIRouter()

orchestrator = AgentOrchestrator()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: str = "default"
    user_id: str = "default"


class ApprovalResolveRequest(BaseModel):
    approval_id: str
    approved: bool
    edited_payload: dict[str, Any] | None = None
    session_id: str = "default"


class ScheduleTaskRequest(BaseModel):
    name: str
    prompt: str
    schedule_type: str = "one_time"
    run_at: str | None = None
    time_of_day: str | None = None
    interval_seconds: int | None = None
    user_id: str = "default"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "personal-ai-agent", "phase": "2"}


@router.get("/integrations")
async def integrations(user_id: str = "default") -> dict[str, Any]:
    from app.observability.health import check_integrations

    report = check_integrations(user_id)
    return report.model_dump(mode="json")


@router.post("/chat", response_model=AgentRunResult)
async def chat(req: ChatRequest) -> AgentRunResult:
    from app.observability.runs import run_store

    ok, reason = run_store.check_cost_limits(req.user_id)
    if not ok:
        return AgentRunResult(
            run_id="cost-limit",
            response=reason,
            status="error",
            error="cost_limit",
        )

    logger.info("chat_request", session_id=req.session_id, message_preview=req.message[:80])
    result = await orchestrator.run(
        req.message,
        session_id=req.session_id,
        user_id=req.user_id,
    )
    run_store.start(
        user_id=req.user_id,
        session_id=req.session_id,
        input_preview=req.message,
    )
    return result


@router.post("/approvals/resolve", response_model=AgentRunResult)
async def resolve_approval(req: ApprovalResolveRequest) -> AgentRunResult:
    return await orchestrator.resolve_approval(
        approval_id=req.approval_id,
        approved=req.approved,
        edited_payload=req.edited_payload,
        session_id=req.session_id,
    )


@router.get("/approvals/pending")
async def list_pending_approvals() -> list[dict[str, Any]]:
    pending = permission_manager.list_pending()
    return [p.model_dump(mode="json") for p in pending]


@router.get("/tools")
async def list_tools() -> list[dict[str, Any]]:
    return [t.model_dump() for t in tool_registry.list_tools()]


@router.get("/runs")
async def list_runs(user_id: str = "default", limit: int = 50) -> list[dict[str, Any]]:
    from app.observability.runs import run_store

    return [r.model_dump(mode="json") for r in run_store.list_for_user(user_id, limit)]


@router.get("/runs/cost")
async def cost_summary(user_id: str = "default") -> dict[str, Any]:
    from app.observability.runs import run_store

    return {
        "daily_usd": run_store.daily_cost(user_id),
        "monthly_usd": run_store.monthly_cost(user_id),
        "limits": run_store.limits.model_dump(),
    }


@router.post("/schedule")
async def schedule_task(req: ScheduleTaskRequest) -> dict[str, Any]:
    from datetime import datetime

    from app.scheduler import scheduler
    from app.scheduler.models import ScheduleKind, ScheduledTask

    try:
        kind = ScheduleKind(req.schedule_type)
    except ValueError:
        raise HTTPException(400, f"Invalid schedule_type: {req.schedule_type}") from None

    run_at = None
    if req.run_at:
        run_at = datetime.fromisoformat(req.run_at.replace("Z", "+00:00"))

    task = ScheduledTask(
        name=req.name,
        prompt=req.prompt,
        kind=kind,
        user_id=req.user_id,
        run_at=run_at,
        time_of_day=req.time_of_day,
        interval_seconds=req.interval_seconds,
    )
    created = scheduler.add(task)
    return created.model_dump(mode="json")


@router.get("/schedule")
async def list_scheduled(user_id: str = "default") -> list[dict[str, Any]]:
    from app.scheduler import scheduler

    return [t.model_dump(mode="json") for t in scheduler.list_tasks(user_id)]


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, str]:
    settings = get_settings()
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(403, "Invalid webhook secret")

    update = await request.json()

    async def agent_handler(user_id: int, text: str) -> str:
        if text.startswith("APPROVE:"):
            aid = text.split(":", 1)[1]
            result = await orchestrator.resolve_approval(aid, approved=True)
            return result.response
        if text.startswith("REJECT:"):
            aid = text.split(":", 1)[1]
            result = await orchestrator.resolve_approval(aid, approved=False)
            return result.response
        result = await orchestrator.run(
            text,
            session_id=f"tg-{user_id}",
            user_id=str(user_id),
        )
        return result.response

    from app.integrations.telegram.bot import TelegramInterface

    iface = TelegramInterface(agent_handler=agent_handler)
    reply = await iface.handle_update(update)
    return {"ok": "true", "reply": reply or ""}
