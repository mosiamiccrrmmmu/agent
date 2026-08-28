from __future__ import annotations

"""API routes."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agent.orchestrator import AgentOrchestrator, AgentRunResult
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


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "personal-ai-agent"}


@router.post("/chat", response_model=AgentRunResult)
async def chat(req: ChatRequest) -> AgentRunResult:
    """Main entry point — send a message to the agent."""
    logger.info("chat_request", session_id=req.session_id, message_preview=req.message[:80])
    result = await orchestrator.run(
        req.message,
        session_id=req.session_id,
        user_id=req.user_id,
    )
    return result


@router.post("/approvals/resolve", response_model=AgentRunResult)
async def resolve_approval(req: ApprovalResolveRequest) -> AgentRunResult:
    """Approve or reject a pending high-risk action."""
    result = await orchestrator.resolve_approval(
        approval_id=req.approval_id,
        approved=req.approved,
        edited_payload=req.edited_payload,
        session_id=req.session_id,
    )
    return result


@router.get("/approvals/pending")
async def list_pending_approvals() -> list[dict[str, Any]]:
    pending = permission_manager.list_pending()
    return [p.model_dump(mode="json") for p in pending]


@router.get("/tools")
async def list_tools() -> list[dict[str, Any]]:
    return [t.model_dump() for t in tool_registry.list_tools()]
