from __future__ import annotations

"""Permission Manager — gatekeeper with SQLite-persisted approvals."""

import hashlib
import json
from datetime import datetime
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger
from app.database.sqlite_store import SQLiteStore, get_store
from app.permissions.models import ApprovalRequest, ApprovalStatus, PermissionDecision
from app.tools.base import RiskLevel

logger = get_logger(__name__)


def canonical_action_hash(tool_name: str, arguments: dict[str, Any]) -> str:
    payload = json.dumps(
        {"tool": tool_name, "args": arguments}, sort_keys=True, default=str, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PermissionManager:
    """Central gatekeeper — approvals survive restart via SQLite."""

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_store()
        self._cache: dict[str, ApprovalRequest] = {}

    def check(
        self,
        tool_name: str,
        risk_level: RiskLevel,
        arguments: dict[str, Any],
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> PermissionDecision:
        settings = get_settings()
        uid = user_id or "default"
        sid = session_id or "default"

        if risk_level == RiskLevel.LOW:
            return PermissionDecision(allowed=True, reason="Low risk — auto allowed")

        if risk_level == RiskLevel.MEDIUM:
            return PermissionDecision(allowed=True, reason="Medium risk — allowed")

        if risk_level == RiskLevel.HIGH:
            if not settings.require_approval_for_high_risk:
                return PermissionDecision(allowed=True, reason="High risk approval disabled")
            request = self._create_request(tool_name, risk_level, arguments, uid, sid)
            return PermissionDecision(
                allowed=False,
                requires_approval=True,
                approval_request=request,
                reason="High risk action requires human approval",
            )

        if not settings.require_approval_for_critical:
            return PermissionDecision(allowed=True, reason="Critical approval disabled (dangerous)")
        request = self._create_request(tool_name, risk_level, arguments, uid, sid)
        return PermissionDecision(
            allowed=False,
            requires_approval=True,
            approval_request=request,
            reason="Critical action requires explicit human approval",
        )

    def _create_request(
        self,
        tool_name: str,
        risk_level: RiskLevel,
        arguments: dict[str, Any],
        user_id: str,
        session_id: str,
    ) -> ApprovalRequest:
        details_str = "\n".join(f"  {k}: {v}" for k, v in arguments.items())
        message = (
            f"Agent wants to execute **{tool_name}** (risk: {risk_level.value})\n\n"
            f"Details:\n{details_str}\n\n"
            f"[ APPROVE ]  [ EDIT ]  [ CANCEL ]"
        )
        action_hash = canonical_action_hash(tool_name, arguments)
        request = ApprovalRequest(
            action=tool_name,
            tool_name=tool_name,
            details=arguments,
            risk_level=risk_level.value,
            action_hash=action_hash,
            user_id=user_id,
            session_id=session_id,
            message_to_user=message,
        )
        self._cache[request.id] = request
        self._persist(request)
        logger.info(
            "approval_requested",
            approval_id=request.id,
            tool=tool_name,
            risk=risk_level.value,
            action_hash=action_hash[:16],
        )
        return request

    def _persist(self, request: ApprovalRequest) -> None:
        self._store.approval_save(request.model_dump(mode="json"))

    def _load(self, approval_id: str) -> ApprovalRequest | None:
        if approval_id in self._cache:
            return self._cache[approval_id]
        row = self._store.approval_get(approval_id)
        if not row:
            return None
        req = ApprovalRequest(**row)
        self._cache[approval_id] = req
        return req

    def get_pending(self, approval_id: str) -> ApprovalRequest | None:
        req = self._load(approval_id)
        if req and req.is_expired() and req.status == ApprovalStatus.PENDING:
            req.status = ApprovalStatus.EXPIRED
            self._persist(req)
        return req

    def resolve(
        self,
        approval_id: str,
        status: ApprovalStatus,
        resolved_by: str = "user",
        edited_payload: dict[str, Any] | None = None,
    ) -> ApprovalRequest | None:
        request = self._load(approval_id)
        if not request:
            return None
        if request.is_expired():
            request.status = ApprovalStatus.EXPIRED
            self._persist(request)
            return request
        if request.consumed or request.status in (
            ApprovalStatus.CONSUMED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
        ):
            return request

        request.status = status
        request.resolved_at = datetime.utcnow()
        request.resolved_by = resolved_by
        if edited_payload is not None:
            request.edited_payload = edited_payload
            request.action_hash = canonical_action_hash(request.tool_name, edited_payload)
            request.status = ApprovalStatus.EDITED
        self._persist(request)
        logger.info("approval_resolved", approval_id=approval_id, status=request.status.value)
        return request

    def consume(
        self,
        approval_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> tuple[bool, str]:
        request = self.get_pending(approval_id)
        if not request:
            return False, "approval_not_found"
        if request.is_expired():
            request.status = ApprovalStatus.EXPIRED
            self._persist(request)
            return False, "approval_expired"
        if request.consumed or request.status == ApprovalStatus.CONSUMED:
            return False, "approval_already_consumed"
        if request.status not in (ApprovalStatus.APPROVED, ApprovalStatus.EDITED):
            return False, f"approval_not_approved:{request.status.value}"
        if request.tool_name != tool_name:
            return False, "tool_mismatch"
        expected = request.edited_payload if request.edited_payload is not None else request.details
        expected_hash = canonical_action_hash(tool_name, expected)
        actual_hash = canonical_action_hash(tool_name, arguments)
        if expected_hash != actual_hash or request.action_hash != expected_hash:
            return False, "argument_mismatch"
        request.consumed = True
        request.status = ApprovalStatus.CONSUMED
        self._persist(request)
        return True, "ok"

    def list_pending(self) -> list[ApprovalRequest]:
        rows = self._store.approval_list_pending()
        out: list[ApprovalRequest] = []
        for row in rows:
            req = ApprovalRequest(**row)
            if req.is_expired():
                req.status = ApprovalStatus.EXPIRED
                self._persist(req)
                continue
            self._cache[req.id] = req
            out.append(req)
        return out


permission_manager = PermissionManager()
