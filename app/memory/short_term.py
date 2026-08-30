from __future__ import annotations

"""Short-term (conversation) memory — SQLite-backed with in-process cache."""

from collections import defaultdict, deque

from app.config import get_settings
from app.database.sqlite_store import SQLiteStore, get_store
from app.llm.base import Message, MessageRole, ToolCall


class ShortTermMemory:
    """Conversation history per session — persisted to SQLite."""

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_store()
        self._sessions: dict[str, deque[Message]] = defaultdict(
            lambda: deque(maxlen=get_settings().short_term_max_messages)
        )
        self._loaded: set[str] = set()

    def _ensure_loaded(self, session_id: str) -> None:
        if session_id in self._loaded:
            return
        max_m = get_settings().short_term_max_messages
        rows = self._store.conversation_get(session_id, limit=max_m)
        for row in rows:
            tool_calls = None
            if row.get("tool_calls"):
                tool_calls = [ToolCall(**tc) for tc in row["tool_calls"]]
            msg = Message(
                role=MessageRole(row["role"]),
                content=row.get("content"),
                tool_call_id=row.get("tool_call_id"),
                name=row.get("name"),
                tool_calls=tool_calls,
            )
            self._sessions[session_id].append(msg)
        self._loaded.add(session_id)

    def add(self, session_id: str, message: Message) -> None:
        self._ensure_loaded(session_id)
        self._sessions[session_id].append(message)
        tool_calls = None
        if message.tool_calls:
            tool_calls = [tc.model_dump() for tc in message.tool_calls]
        self._store.conversation_append(
            session_id,
            role=message.role.value,
            content=message.content,
            tool_call_id=message.tool_call_id,
            name=message.name,
            tool_calls=tool_calls,
        )

    def get(self, session_id: str) -> list[Message]:
        self._ensure_loaded(session_id)
        return list(self._sessions.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._sessions[session_id].clear()
        self._store.conversation_clear(session_id)
        self._loaded.add(session_id)

    def get_context_window(self, session_id: str, max_messages: int | None = None) -> list[Message]:
        messages = self.get(session_id)
        if max_messages:
            return messages[-max_messages:]
        return messages
