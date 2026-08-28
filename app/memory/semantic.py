from __future__ import annotations

"""Semantic memory placeholder (pgvector later)."""

from typing import Any

from pydantic import BaseModel, Field


class SemanticMemoryItem(BaseModel):
    id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticMemory:
    """Placeholder. Will use pgvector + embedding model in Phase 2."""

    def __init__(self) -> None:
        self._items: list[SemanticMemoryItem] = []

    async def add(self, content: str, embedding: list[float] | None = None, **meta: Any) -> SemanticMemoryItem:
        from uuid import uuid4

        item = SemanticMemoryItem(
            id=str(uuid4()),
            content=content,
            embedding=embedding,
            metadata=meta,
        )
        self._items.append(item)
        return item

    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[SemanticMemoryItem]:
        # MVP: no real vector search yet
        return self._items[:top_k]
