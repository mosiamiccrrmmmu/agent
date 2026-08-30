"""Adversarial approval security tests."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_appr.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test_appr.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")

from app.permissions.manager import PermissionManager, canonical_action_hash
from app.permissions.models import ApprovalStatus
from app.tools.base import RiskLevel


@pytest.fixture
def pm():
    return PermissionManager()


def test_action_hash_stable():
    a = canonical_action_hash("send_email", {"to": "a@b.com", "subject": "Hi", "body": "x"})
    b = canonical_action_hash("send_email", {"body": "x", "subject": "Hi", "to": "a@b.com"})
    assert a == b


def test_action_hash_differs_on_recipient():
    a = canonical_action_hash("send_whatsapp", {"chat_id": "Ali", "body": "hello"})
    b = canonical_action_hash("send_whatsapp", {"chat_id": "Reza", "body": "hello"})
    assert a != b


def test_high_risk_requires_approval(pm):
    d = pm.check("send_email", RiskLevel.HIGH, {"to": "x@y.com", "subject": "s", "body": "b"})
    assert d.requires_approval is True
    assert d.approval_request is not None
    assert d.approval_request.action_hash


def test_consume_rejects_argument_mismatch(pm):
    d = pm.check("send_whatsapp", RiskLevel.HIGH, {"chat_id": "Ali", "body": "hi"})
    aid = d.approval_request.id
    pm.resolve(aid, ApprovalStatus.APPROVED)
    ok, reason = pm.consume(aid, "send_whatsapp", {"chat_id": "Reza", "body": "hi"})
    assert ok is False
    assert reason == "argument_mismatch"


def test_consume_rejects_tool_mismatch(pm):
    d = pm.check("send_whatsapp", RiskLevel.HIGH, {"chat_id": "Ali", "body": "hi"})
    aid = d.approval_request.id
    pm.resolve(aid, ApprovalStatus.APPROVED)
    ok, reason = pm.consume(aid, "send_email", {"chat_id": "Ali", "body": "hi"})
    assert ok is False
    assert reason == "tool_mismatch"


def test_consume_rejects_replay(pm):
    args = {"chat_id": "Ali", "body": "hi"}
    d = pm.check("send_whatsapp", RiskLevel.HIGH, args)
    aid = d.approval_request.id
    pm.resolve(aid, ApprovalStatus.APPROVED)
    ok1, _ = pm.consume(aid, "send_whatsapp", args)
    assert ok1 is True
    ok2, reason = pm.consume(aid, "send_whatsapp", args)
    assert ok2 is False
    assert reason == "approval_already_consumed"


def test_expired_approval(pm):
    d = pm.check("send_whatsapp", RiskLevel.HIGH, {"chat_id": "Ali", "body": "hi"})
    req = d.approval_request
    req.expires_at = datetime.utcnow() - timedelta(minutes=1)
    ok, reason = pm.consume(req.id, "send_whatsapp", {"chat_id": "Ali", "body": "hi"})
    assert ok is False
    assert reason == "approval_expired"
