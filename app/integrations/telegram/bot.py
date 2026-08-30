"""Telegram as primary control interface."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

COMMANDS = {
    "/help": "Show available commands",
    "/status": "Integration status",
    "/tasks": "List scheduled tasks",
    "/memory": "Show recent memories",
    "/approve": "Approve a pending action: /approve <id>",
    "/reject": "Reject a pending action: /reject <id>",
    "/chat": "Talk to the agent",
}


class TelegramInterface:
    def __init__(self, agent_handler: Callable[[int, str], Awaitable[str]] | None = None) -> None:
        settings = get_settings()
        self.token = settings.telegram_bot_token
        self.allowed_ids = settings.allowed_telegram_user_ids
        self.agent_handler = agent_handler

    def is_authorized(self, user_id: int) -> bool:
        if not self.allowed_ids:
            return True
        return user_id in self.allowed_ids

    async def handle_update(self, update: dict[str, Any]) -> str | None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return None
        user = message.get("from") or {}
        user_id = int(user.get("id", 0))
        text = (message.get("text") or "").strip()
        if not text:
            return None
        if not self.is_authorized(user_id):
            return "Unauthorized."

        if text.startswith("/help"):
            lines = [f"{k} — {v}" for k, v in COMMANDS.items()]
            return "Personal AI Agent commands:\n" + "\n".join(lines)

        if text.startswith("/status"):
            from app.observability.health import check_integrations

            report = check_integrations(str(user_id))
            lines = [f"{i.name}: {i.status.value}" for i in report.integrations]
            return "Integrations:\n" + "\n".join(lines)

        if text.startswith("/tasks"):
            from app.scheduler import scheduler

            tasks = scheduler.list_tasks(str(user_id))
            if not tasks:
                return "No scheduled tasks."
            return "\n".join(f"- {t.name} [{t.status.value}] next={t.next_run_at}" for t in tasks)

        if text.startswith("/memory"):
            from app.memory.long_term import LongTermMemory

            items = LongTermMemory().list()[:10]
            if not items:
                return "No memories stored."
            return "\n".join(f"- {m.content}" for m in items)

        if text.startswith("/approve "):
            approval_id = text.split(maxsplit=1)[1].strip()
            if self.agent_handler:
                return await self.agent_handler(user_id, f"APPROVE:{approval_id}")
            return f"Approval {approval_id} received (wire agent_handler)."

        if text.startswith("/reject "):
            approval_id = text.split(maxsplit=1)[1].strip()
            if self.agent_handler:
                return await self.agent_handler(user_id, f"REJECT:{approval_id}")
            return f"Rejection {approval_id} received."

        if text.startswith("/chat"):
            text = text[len("/chat") :].strip() or "Hello"

        if self.agent_handler:
            return await self.agent_handler(user_id, text)
        return f"(no agent handler) You said: {text}"
