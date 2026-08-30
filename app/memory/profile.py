from __future__ import annotations

"""User Profile memory — SQLite-backed."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.database.sqlite_store import SQLiteStore, get_store


class UserProfile(BaseModel):
    user_id: str = "default"
    name: str | None = None
    language: str = "fa"
    timezone: str = "Asia/Tehran"
    communication_style: str = "friendly_professional"
    important_contacts: list[dict[str, str]] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    work_patterns: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProfileStore:
    """Durable profile store."""

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_store()

    def get(self, user_id: str = "default") -> UserProfile:
        data = self._store.profile_get(user_id)
        if not data:
            profile = UserProfile(user_id=user_id)
            self._store.profile_set(user_id, profile.model_dump(mode="json"))
            return profile
        if "updated_at" in data and isinstance(data["updated_at"], str):
            try:
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            except ValueError:
                data["updated_at"] = datetime.utcnow()
        return UserProfile(**data)

    def update(self, user_id: str = "default", **kwargs: Any) -> UserProfile:
        profile = self.get(user_id)
        for k, v in kwargs.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        profile.updated_at = datetime.utcnow()
        self._store.profile_set(user_id, profile.model_dump(mode="json"))
        return profile
