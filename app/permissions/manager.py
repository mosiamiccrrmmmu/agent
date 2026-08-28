from __future__ import annotations

"""Permission Manager — decides whether a tool may run and creates approval requests."""

from typing import Any

from app.config import get_settings
from app.core.logging import get_logger
from app.permissions.models import ApprovalRequest, ApprovalStatus, PermissionDecision
from app.tools.base import RiskLevel

logger = get_logger(__name__)


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
    ) -> PermissionDecision:
        settings = get_settings()

        if risk_level == RiskLevel.LOW:
            return PermissionDecision(allowed=True, reason="Low risk — auto allowed")

        if risk_level == RiskLevel.MEDIUM:
            return PermissionDecision(allowed=True, reason="Medium risk — allowed")

        if risk_level == RiskLevel.HIGH:
            if not settings.require_approval_for_high_risk:
                return PermissionDecision(allowed=True, reason="High risk approval disabled")
            request = self._create_request(tool_name, risk_level, arguments)
            return PermissionDecision(
                allowed=False,
                requires_approval=True,
                approval_request=request,
                reason="High risk action requires human approval",
            )

        if not settings.require_approval_for_critical:
            return PermissionDecision(allowed=True, reason="Critical approval disabled (dangerous)")
        request = self._create_request(tool_name, risk_level, arguments)
        return PermissionDecision(
            allowed=False,
            requires_approval=True,
            approval_request=request,
            reason="Critical action requires explicit human approval",
        )

    def _create_request(
        self, tool_name: str, risk_level: RiskLevel, arguments: dict[str, Any]
    ) -> ApprovalRequest:
        details_str = "\n".join(f"  {k}: {v}" for k, v in arguments.items())
        message = (
            f"Agent wants to execute **{tool_name}** (risk: {risk_level.value})\n\n"
            f"Details:\n{details_str}\n\n"
            f"[ APPROVE ]  [ EDIT ]  [ CANCEL ]"
        )
        request = ApprovalRequest(
            action=tool_name,
            tool_name=tool_name,
            details=arguments,
            risk_level=risk_level.value,
            message_to_user=message,
        )
        self._pending[request.id] = request
        logger.info(
            "approval_requested",
            approval_id=request.id,
            tool=tool_name,
            risk=risk_level.value,
        )
        return request

    def get_pending(self, approval_id: str) -> ApprovalRequest | None:
        return self._pending.get(approval_id)

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
        request.status = status
        request.resolved_at = __import__("datetime").datetime.utcnow()
        request.resolved_by = resolved_by
        if edited_payload is not None:
            request.edited_payload = edited_payload
            request.status = ApprovalStatus.EDITED
        logger.info(
            "approval_resolved",
            approval_id=approval_id,
            status=status.value,
        )
        return request

    def list_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._pending.values() if r.status == ApprovalStatus.PENDING]


permission_manager = PermissionManager()
