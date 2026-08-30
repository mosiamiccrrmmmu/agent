from __future__ import annotations

"""Long-term memory — SQLite-backed for desktop durability."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.database.sqlite_store import SQLiteStore, get_store


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
    """Durable long-term memory (SQLite)."""

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_store()

    def add(
        self, content: str, category: str = "general", source: str = "user", **meta: Any
    ) -> MemoryItem:
        item = MemoryItem(content=content, category=category, source=source, metadata=meta)
        self._store.ltm_add(
            item.id,
            item.content,
            category=item.category,
            source=item.source,
            metadata=item.metadata,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        return item

    def get(self, item_id: str) -> MemoryItem | None:
        row = self._store.ltm_get(item_id)
        if not row:
            return None
        return MemoryItem(**row)

    def list(self, category: str | None = None, active_only: bool = True) -> list[MemoryItem]:
        return [MemoryItem(**r) for r in self._store.ltm_list(category=category, active_only=active_only)]

    def update(self, item_id: str, content: str | None = None, **kwargs: Any) -> MemoryItem | None:
        fields: dict[str, Any] = dict(kwargs)
        if content is not None:
            fields["content"] = content
        if not self._store.ltm_update(item_id, **fields):
            return None
        return self.get(item_id)

    def delete(self, item_id: str) -> bool:
        return self._store.ltm_delete(item_id)

    def search(self, query: str) -> list[MemoryItem]:
        return [MemoryItem(**r) for r in self._store.ltm_search(query)]
