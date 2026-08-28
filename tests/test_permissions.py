"""Permission system unit tests."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://agent:agent@localhost:5432/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://agent:agent@localhost:5432/test")

from app.permissions.manager import PermissionManager
from app.tools.base import RiskLevel


def test_low_risk_allowed():
    pm = PermissionManager()
    decision = pm.check("search_web", RiskLevel.LOW, {"query": "test"})
    assert decision.allowed is True
    assert decision.requires_approval is False


def test_high_risk_requires_approval():
    pm = PermissionManager()
    decision = pm.check("send_email", RiskLevel.HIGH, {"to": "a@b.com", "body": "hi"})
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.approval_request is not None
    assert decision.approval_request.tool_name == "send_email"


def test_critical_requires_approval():
    pm = PermissionManager()
    decision = pm.check("delete_account", RiskLevel.CRITICAL, {})
    assert decision.requires_approval is True
