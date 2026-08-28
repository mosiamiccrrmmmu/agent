from __future__ import annotations

"""User Profile memory."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
    """In-memory profile store for MVP."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def get(self, user_id: str = "default") -> UserProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]

    def update(self, user_id: str = "default", **kwargs: Any) -> UserProfile:
        profile = self.get(user_id)
        for k, v in kwargs.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        profile.updated_at = datetime.utcnow()
        return profile
