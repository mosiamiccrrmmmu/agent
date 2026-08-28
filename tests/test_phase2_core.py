"""Phase 2 unit tests — integrations scaffolding, policy, scheduler, health."""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://agent:agent@localhost:5432/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://agent:agent@localhost:5432/test")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEBUG", "true")

import pytest
from fastapi.testclient import TestClient

from app.computer.policy import ComputerAction, ComputerPolicy
from app.integrations.telegram.bot import TelegramInterface
from app.observability.health import IntegrationStatus, check_integrations
from app.scheduler.engine import Scheduler
from app.scheduler.models import ScheduleKind, ScheduledTask
from app.tools.base import RiskLevel


def test_computer_policy_risk_levels():
    policy = ComputerPolicy()
    assert policy.risk_for(ComputerAction.SCREENSHOT) == RiskLevel.LOW
    assert policy.risk_for(ComputerAction.CLICK) in (
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
        RiskLevel.LOW,
    )
    for action in ComputerAction:
        risk = policy.risk_for(action)
        assert risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)


def test_integration_health_report():
    report = check_integrations("default")
    names = {i.name for i in report.integrations}
    assert "llm" in names
    assert "database" in names
    assert "gmail" in names
    assert "telegram" in names
    assert "whatsapp" in names
    assert "browser" in names


def test_scheduler_add_and_list():
    sched = Scheduler()
    task = ScheduledTask(
        name="morning",
        prompt="Brief me",
        kind=ScheduleKind.DAILY,
        time_of_day="08:00",
        user_id="u1",
    )
    created = sched.add(task)
    assert created.id
    listed = sched.list_tasks("u1")
    assert any(t.name == "morning" for t in listed)


@pytest.mark.asyncio
async def test_telegram_help_command():
    iface = TelegramInterface()
    reply = await iface.handle_update(
        {"message": {"text": "/help", "from": {"id": 1}, "chat": {"id": 1}}}
    )
    assert reply is not None
    assert "/status" in reply


@pytest.mark.asyncio
async def test_telegram_unauthorized_when_allowlist():
    iface = TelegramInterface()
    iface.allowed_ids = [999]
    reply = await iface.handle_update(
        {"message": {"text": "hello", "from": {"id": 1}, "chat": {"id": 1}}}
    )
    assert reply == "Unauthorized."


def test_phase2_tools_registered_on_app():
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/v1/tools")
        assert r.status_code == 200
        names = {t["name"] for t in r.json()}
        assert "search_web" in names


def test_integrations_endpoint():
    from app.main import create_app

    with TestClient(create_app()) as client:
        r = client.get("/api/v1/integrations")
        assert r.status_code == 200
        data = r.json()
        assert "integrations" in data


def test_send_email_is_high_risk():
    from app.tools.gmail.tools import SendEmailTool

    tool = SendEmailTool()
    assert tool.metadata.risk_level == RiskLevel.HIGH


def test_send_whatsapp_is_high_risk():
    from app.tools.whatsapp.tools import SendWhatsAppTool

    tool = SendWhatsAppTool()
    assert tool.metadata.risk_level == RiskLevel.HIGH
