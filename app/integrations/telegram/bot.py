"""Telegram as primary control interface."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MessageHandler = Callable[[int, str], Awaitable[str]]


COMMANDS = {
    "/help": "Show available commands",
    "/status": "Integration health",
    "/tasks": "List scheduled tasks",
    "/memory": "Show recent long-term memories",
    "/approve": "Approve pending action: /approve <approval_id>",
    "/reject": "Reject pending action: /reject <approval_id>",
    "/chat": "Chat with the agent (or just send natural language)",
}


class TelegramInterface:
    """Handles commands + natural language → Agent."""

    def __init__(self, agent_handler: MessageHandler | None = None) -> None:
        self.agent_handler = agent_handler
        settings = get_settings()
        self.bot_token = settings.telegram_bot_token
        self.allowed_ids = settings.allowed_telegram_user_ids

    def is_authorized(self, user_id: int) -> bool:
        if not self.allowed_ids:
            return True  # open in dev if not configured
        return user_id in self.allowed_ids

    async def handle_update(self, update: dict[str, Any]) -> str | None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return None
        chat = message.get("chat") or {}
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

        # Natural language → agent
        if self.agent_handler:
            return await self.agent_handler(user_id, text)
        return f"(no agent handler) You said: {text}"
