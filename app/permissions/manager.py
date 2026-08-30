from __future__ import annotations

"""Permission Manager — decides whether a tool may run and creates approval requests."""

import hashlib
import json
from datetime import datetime
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger
from app.permissions.models import ApprovalRequest, ApprovalStatus, PermissionDecision
from app.tools.base import RiskLevel

logger = get_logger(__name__)


def canonical_action_hash(tool_name: str, arguments: dict[str, Any]) -> str:
    """Stable hash of tool + sorted JSON arguments."""
    payload = json.dumps(
        {"tool": tool_name, "args": arguments}, sort_keys=True, default=str, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PermissionManager:
    """Central gatekeeper for tool execution."""

    def __init__(self) -> None:
        self._pending: dict[str, ApprovalRequest] = {}

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
        self._pending[request.id] = request
        logger.info(
            "approval_requested",
            approval_id=request.id,
            tool=tool_name,
            risk=risk_level.value,
            action_hash=action_hash[:16],
        )
        return request

    def get_pending(self, approval_id: str) -> ApprovalRequest | None:
        req = self._pending.get(approval_id)
        if req and req.is_expired() and req.status == ApprovalStatus.PENDING:
            req.status = ApprovalStatus.EXPIRED
        return req

    def resolve(
        self,
        approval_id: str,
        status: ApprovalStatus,
        resolved_by: str = "user",
        edited_payload: dict[str, Any] | None = None,
    ) -> ApprovalRequest | None:
        request = self._pending.get(approval_id)
        if not request:
            return None
        if request.is_expired():
            request.status = ApprovalStatus.EXPIRED
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
            # Re-bind hash to edited payload — original approval does not cover new args
            request.edited_payload = edited_payload
            request.action_hash = canonical_action_hash(request.tool_name, edited_payload)
            request.status = ApprovalStatus.EDITED
        logger.info(
            "approval_resolved",
            approval_id=approval_id,
            status=request.status.value,
        )
        return request

    def consume(
        self,
        approval_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> tuple[bool, str]:
        """Validate binding and mark approval as consumed (single use)."""
        request = self.get_pending(approval_id)
        if not request:
            return False, "approval_not_found"
        if request.is_expired():
            request.status = ApprovalStatus.EXPIRED
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
        return True, "ok"

    def list_pending(self) -> list[ApprovalRequest]:
        out: list[ApprovalRequest] = []
        for r in self._pending.values():
            if r.is_expired() and r.status == ApprovalStatus.PENDING:
                r.status = ApprovalStatus.EXPIRED
            if r.status == ApprovalStatus.PENDING:
                out.append(r)
        return out


permission_manager = PermissionManager()
