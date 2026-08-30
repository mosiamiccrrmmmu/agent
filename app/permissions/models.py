from __future__ import annotations

"""Permission and Approval models."""

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ApprovalRequest(BaseModel):
    """A request for human approval before executing a high-risk action.

    action_hash binds the approval to canonical (tool + arguments).
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    tool_name: str
    details: dict[str, Any]
    risk_level: str
    action_hash: str = ""
    user_id: str = "default"
    session_id: str = "default"
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=15)
    )
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    edited_payload: dict[str, Any] | None = None
    message_to_user: str = ""
    consumed: bool = False

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class PermissionDecision(BaseModel):
    """Result of a permission check."""

    allowed: bool
    requires_approval: bool = False
    approval_request: ApprovalRequest | None = None
    reason: str = ""
