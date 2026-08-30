from __future__ import annotations

"""Agent Orchestrator — the core agent loop.

User Request → Understand → Memory → Plan → Tools → Permission → Execute → Reflect → Respond
"""

import asyncio
import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agent.cancel import clear_agent_cancel, is_agent_cancelled
from app.config import get_settings
from app.core.logging import get_logger
from app.llm.base import Message, MessageRole, ToolCall, ToolDefinition
from app.llm.factory import TaskType, llm_factory
from app.memory.long_term import LongTermMemory
from app.memory.profile import ProfileStore
from app.memory.short_term import ShortTermMemory
from app.permissions.manager import permission_manager
from app.permissions.models import ApprovalStatus
from app.tools.base import ToolResult
from app.tools.registry import tool_registry

logger = get_logger(__name__)


class AgentRunResult(BaseModel):
    run_id: str
    response: str
    tools_used: list[str] = Field(default_factory=list)
    steps: int = 0
    duration_ms: float = 0.0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    status: str = "completed"
    approval_id: str | None = None
    error: str | None = None


SYSTEM_PROMPT = """You are a Personal AI Agent — a capable, careful assistant that helps the user with real tasks.

Core principles:
1. Be precise and useful. Prefer action over vague advice.
2. Use tools when you need real data or to perform actions.
3. Never invent facts that should come from tools or databases.
4. For any action that sends messages, emails, deletes data, or has external side-effects, you must respect the permission system.
5. Keep responses concise unless the user asks for detail.
6. Remember important facts only when the user explicitly asks you to, or when it is clearly durable information.
7. Communicate in the user's preferred language (default: Persian/Farsi).

You have access to tools. Use them when needed.
When you need clarification, ask the user.
When a high-risk action is required, the system will request approval automatically.
"""


def _cancelled_result(
    *,
    run_id: str,
    tools_used: list[str],
    steps: int,
    start: float,
    total_tokens: int,
    total_cost: float,
) -> AgentRunResult:
    clear_agent_cancel()
    duration = (time.perf_counter() - start) * 1000
    logger.info("agent_cancelled", run_id=run_id, step=steps)
    return AgentRunResult(
        run_id=run_id,
        response="Stopped by user.",
        tools_used=tools_used,
        steps=steps,
        duration_ms=duration,
        total_tokens=total_tokens,
        estimated_cost_usd=total_cost,
        status="cancelled",
        error="CANCELLED",
    )


class AgentOrchestrator:
    """Main agent runtime."""

    def __init__(
        self,
        short_term: ShortTermMemory | None = None,
        long_term: LongTermMemory | None = None,
        profile_store: ProfileStore | None = None,
    ) -> None:
        self.short_term = short_term or ShortTermMemory()
        self.long_term = long_term or LongTermMemory()
        self.profile = profile_store or ProfileStore()

    async def run(
        self,
        user_message: str,
        *,
        session_id: str = "default",
        user_id: str = "default",
        max_steps: int | None = None,
    ) -> AgentRunResult:
        settings = get_settings()
        max_steps = max_steps or settings.max_agent_steps
        run_id = str(uuid4())
        start = time.perf_counter()

        tools_used: list[str] = []
        total_tokens = 0
        total_cost = 0.0
        steps = 0

        logger.info("agent_run_started", run_id=run_id, session_id=session_id)

        self.short_term.add(
            session_id,
            Message(role=MessageRole.USER, content=user_message),
        )

        profile = self.profile.get(user_id)
        memory_items = self.long_term.list()[:10]
        memory_context = ""
        if memory_items:
            memory_context = "\nKnown facts about the user:\n" + "\n".join(
                f"- {m.content}" for m in memory_items
            )

        system = SYSTEM_PROMPT
        if profile.name:
            system += f"\nUser name: {profile.name}"
        system += f"\nPreferred language: {profile.language}"
        system += memory_context

        messages: list[Message] = [
            Message(role=MessageRole.SYSTEM, content=system),
            *self.short_term.get_context_window(session_id),
        ]

        tool_defs = [
            ToolDefinition(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
            )
            for t in tool_registry.list_for_llm()
        ]

        provider, model = llm_factory.resolve_model(TaskType.GENERAL)

        try:
            async with asyncio.timeout(settings.agent_timeout_seconds):
                while steps < max_steps:
                    if is_agent_cancelled():
                        return _cancelled_result(
                            run_id=run_id,
                            tools_used=tools_used,
                            steps=steps,
                            start=start,
                            total_tokens=total_tokens,
                            total_cost=total_cost,
                        )
                    steps += 1
                    logger.debug("agent_step", run_id=run_id, step=steps)

                    response = await provider.generate(
                        messages,
                        model=model,
                        tools=tool_defs if tool_defs else None,
                        temperature=0.2,
                    )

                    total_tokens += response.usage.total_tokens
                    total_cost += response.usage.estimated_cost_usd

                    if not response.tool_calls:
                        final = response.content or ""
                        self.short_term.add(
                            session_id,
                            Message(role=MessageRole.ASSISTANT, content=final),
                        )
                        duration = (time.perf_counter() - start) * 1000
                        return AgentRunResult(
                            run_id=run_id,
                            response=final,
                            tools_used=tools_used,
                            steps=steps,
                            duration_ms=duration,
                            total_tokens=total_tokens,
                            estimated_cost_usd=total_cost,
                            status="completed",
                        )

                    messages.append(
                        Message(
                            role=MessageRole.ASSISTANT,
                            content=response.content,
                            tool_calls=response.tool_calls,
                        )
                    )

                    for tc in response.tool_calls:
                        if is_agent_cancelled():
                            return _cancelled_result(
                                run_id=run_id,
                                tools_used=tools_used,
                                steps=steps,
                                start=start,
                                total_tokens=total_tokens,
                                total_cost=total_cost,
                            )
                        tools_used.append(tc.name)
                        result = await self._execute_tool(
                            tc, user_id=user_id, session_id=session_id
                        )

                        if result.requires_approval and result.approval_id:
                            duration = (time.perf_counter() - start) * 1000
                            return AgentRunResult(
                                run_id=run_id,
                                response=(
                                    result.data.get("message", "Approval required")
                                    if isinstance(result.data, dict)
                                    else "Approval required for this action."
                                ),
                                tools_used=tools_used,
                                steps=steps,
                                duration_ms=duration,
                                total_tokens=total_tokens,
                                estimated_cost_usd=total_cost,
                                status="needs_approval",
                                approval_id=result.approval_id,
                            )

                        tool_content = (
                            str(result.data)
                            if result.success
                            else f"Error: {result.error}"
                        )
                        messages.append(
                            Message(
                                role=MessageRole.TOOL,
                                content=tool_content,
                                tool_call_id=tc.id,
                                name=tc.name,
                            )
                        )
                        self.short_term.add(
                            session_id,
                            Message(
                                role=MessageRole.TOOL,
                                content=tool_content,
                                tool_call_id=tc.id,
                                name=tc.name,
                            ),
                        )

                duration = (time.perf_counter() - start) * 1000
                return AgentRunResult(
                    run_id=run_id,
                    response=(
                        "I reached the maximum number of steps. "
                        "Please try a more specific request."
                    ),
                    tools_used=tools_used,
                    steps=steps,
                    duration_ms=duration,
                    total_tokens=total_tokens,
                    estimated_cost_usd=total_cost,
                    status="error",
                    error="max_steps_exceeded",
                )

        except TimeoutError:
            duration = (time.perf_counter() - start) * 1000
            logger.error("agent_timeout", run_id=run_id)
            return AgentRunResult(
                run_id=run_id,
                response="The request timed out. Please try again with a simpler task.",
                tools_used=tools_used,
                steps=steps,
                duration_ms=duration,
                total_tokens=total_tokens,
                estimated_cost_usd=total_cost,
                status="timeout",
                error="timeout",
            )
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            logger.exception("agent_error", run_id=run_id)
            return AgentRunResult(
                run_id=run_id,
                response=f"An error occurred: {exc}",
                tools_used=tools_used,
                steps=steps,
                duration_ms=duration,
                total_tokens=total_tokens,
                estimated_cost_usd=total_cost,
                status="error",
                error=str(exc),
            )

    async def _execute_tool(
        self,
        tool_call: ToolCall,
        user_id: str = "default",
        session_id: str = "default",
    ) -> ToolResult:
        if is_agent_cancelled():
            return ToolResult(success=False, error="CANCELLED")

        tool = tool_registry.get(tool_call.name)
        if tool is None:
            return ToolResult(success=False, error=f"Unknown tool: {tool_call.name}")

        decision = permission_manager.check(
            tool_name=tool_call.name,
            risk_level=tool.metadata.risk_level,
            arguments=tool_call.arguments,
            user_id=user_id,
            session_id=session_id,
        )

        if decision.requires_approval and decision.approval_request:
            return ToolResult(
                success=False,
                requires_approval=True,
                approval_id=decision.approval_request.id,
                data={"message": decision.approval_request.message_to_user},
            )

        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)

        return await tool_registry.execute(tool_call.name, tool_call.arguments)

    async def resolve_approval(
        self,
        approval_id: str,
        approved: bool,
        edited_payload: dict[str, Any] | None = None,
        session_id: str = "default",
    ) -> AgentRunResult:
        """Continue after human approval — single-use, argument-bound."""
        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request = permission_manager.resolve(
            approval_id, status, edited_payload=edited_payload
        )
        if not request:
            return AgentRunResult(
                run_id=str(uuid4()),
                response="Approval request not found or already resolved.",
                status="error",
                error="approval_not_found",
            )

        if request.status == ApprovalStatus.EXPIRED:
            return AgentRunResult(
                run_id=str(uuid4()),
                response="Approval request has expired. Please try the action again.",
                status="error",
                error="approval_expired",
            )

        if not approved:
            return AgentRunResult(
                run_id=str(uuid4()),
                response="Action cancelled by user.",
                status="completed",
            )

        payload = edited_payload if edited_payload is not None else request.details
        ok, reason = permission_manager.consume(
            approval_id, request.tool_name, payload
        )
        if not ok:
            return AgentRunResult(
                run_id=str(uuid4()),
                response=f"Approval could not be used: {reason}",
                status="error",
                error=reason,
            )

        result = await tool_registry.execute(request.tool_name, payload)

        if result.success:
            msg = f"Action completed successfully.\nResult: {result.data}"
        else:
            msg = f"Action failed: {result.error}"

        return AgentRunResult(
            run_id=str(uuid4()),
            response=msg,
            tools_used=[request.tool_name],
            status="completed" if result.success else "error",
            error=result.error,
        )
