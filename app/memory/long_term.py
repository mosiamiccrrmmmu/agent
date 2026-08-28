from __future__ import annotations

"""Long-term memory (facts the user wants the agent to remember)."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    category: str = "general"
    source: str = "user"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class LongTermMemory:
    """Simple in-memory store for MVP. Later backed by PostgreSQL."""

    def __init__(self) -> None:
        self._items: dict[str, MemoryItem] = {}

    def add(self, content: str, category: str = "general", source: str = "user", **meta: Any) -> MemoryItem:
        item = MemoryItem(content=content, category=category, source=source, metadata=meta)
        self._items[item.id] = item
        return item

    def get(self, item_id: str) -> MemoryItem | None:
        return self._items.get(item_id)

    def list(self, category: str | None = None, active_only: bool = True) -> list[MemoryItem]:
        items = list(self._items.values())
        if active_only:
            items = [i for i in items if i.active]
        if category:
            items = [i for i in items if i.category == category]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def update(self, item_id: str, content: str | None = None, **kwargs: Any) -> MemoryItem | None:
        item = self._items.get(item_id)
        if not item:
            return None
        if content is not None:
            item.content = content
        for k, v in kwargs.items():
            if hasattr(item, k):
                setattr(item, k, v)
        item.updated_at = datetime.utcnow()
        return item

    def delete(self, item_id: str) -> bool:
        item = self._items.get(item_id)
        if not item:
            return False
        item.active = False
        item.updated_at = datetime.utcnow()
        return True

    def search(self, query: str) -> list[MemoryItem]:
        """Naive keyword search for MVP. Will be replaced by semantic search."""
        q = query.lower()
        return [i for i in self.list() if q in i.content.lower()]
