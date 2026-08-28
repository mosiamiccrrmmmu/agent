from __future__ import annotations

"""Short-term (conversation) memory."""

from collections import defaultdict, deque

from app.config import get_settings
from app.llm.base import Message


class ShortTermMemory:
    """In-memory conversation history per session/user."""

    def __init__(self) -> None:
        self._sessions: dict[str, deque[Message]] = defaultdict(
            lambda: deque(maxlen=get_settings().short_term_max_messages)
        )

    def add(self, session_id: str, message: Message) -> None:
        self._sessions[session_id].append(message)

    def get(self, session_id: str) -> list[Message]:
        return list(self._sessions.get(session_id, []))

    def clear(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].clear()

    def get_context_window(self, session_id: str, max_messages: int | None = None) -> list[Message]:
        messages = self.get(session_id)
        if max_messages:
            return messages[-max_messages:]
        return messages
