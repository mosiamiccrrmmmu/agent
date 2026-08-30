"""End-to-End Agent flow tests using Mock LLM Provider.

Path tested:
  Request → FastAPI → Orchestrator → LLM (mock) → Tool Registry
  → Permission Manager → Tool execution → Memory → Response
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ["SECRET_KEY"] = "test-secret-key-at-least-16-chars"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_e2e.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test_e2e.db"
os.environ["DEFAULT_LLM_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "development"
os.environ["DEBUG"] = "true"
os.environ["REQUIRE_LOCAL_AUTH"] = "false"

from app.agent.orchestrator import AgentOrchestrator
from app.config.settings import get_settings
from app.llm.factory import llm_factory
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.permissions.manager import permission_manager
from app.tools.base import RiskLevel
from app.tools.memory_tools import RecallTool, RememberTool
from app.tools.registry import tool_registry
from app.tools.web.search import WebSearchTool

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def setup_mock_and_tools():
    llm_factory.clear()
    mock = MockLLMProvider(default_response="سلام! من دستیار شخصی شما هستم.")
    llm_factory.register_provider("mock", mock)
    tool_registry._tools.clear()
    tool_registry.register(WebSearchTool())
    tool_registry.register(RememberTool())
    tool_registry.register(RecallTool())
    permission_manager._cache.clear()
    yield
    llm_factory.clear()
    tool_registry._tools.clear()


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def orchestrator():
    return AgentOrchestrator()


def test_health_endpoint(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_desktop_setup_status(client):
    r = client.get("/api/v1/desktop/setup/status")
    assert r.status_code == 200
    data = r.json()
    assert "providers" in data
    assert data["providers"]["grok"] in ("connected", "not_configured")


def test_tools_listed(client):
    r = client.get("/api/v1/tools")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()}
    assert "search_web" in names
    assert "remember" in names
    assert "recall" in names


@pytest.mark.asyncio
async def test_agent_simple_chat(orchestrator):
    result = await orchestrator.run("سلام", session_id="e2e-simple")
    assert result.status == "completed"
    assert result.response
    assert result.run_id


@pytest.mark.asyncio
async def test_agent_tool_call_path(orchestrator):
    result = await orchestrator.run("please search the web for news", session_id="e2e-tool")
    assert result.status in ("completed", "needs_approval", "error")
    assert result.run_id


@pytest.mark.asyncio
async def test_high_risk_blocked_without_approval():
    from app.tools.base import BaseTool, ToolMetadata, ToolResult

    class FakeHighRiskTool(BaseTool):
        metadata = ToolMetadata(
            name="send_fake_email",
            description="Fake high-risk tool",
            input_schema={"type": "object", "properties": {"to": {"type": "string"}}, "required": ["to"]},
            risk_level=RiskLevel.HIGH,
        )

        async def execute(self, **kwargs):
            return ToolResult(success=True, data="sent")

    tool_registry.register(FakeHighRiskTool())
    decision = permission_manager.check(
        "send_fake_email", RiskLevel.HIGH, {"to": "test@example.com"}
    )
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.approval_request is not None


@pytest.mark.asyncio
async def test_critical_risk_blocked():
    decision = permission_manager.check("delete_everything", RiskLevel.CRITICAL, {})
    assert decision.requires_approval is True


@pytest.mark.asyncio
async def test_memory_session_isolation(orchestrator):
    await orchestrator.run("من علی هستم", session_id="user-a")
    await orchestrator.run("من سارا هستم", session_id="user-b")
    msgs_a = orchestrator.short_term.get("user-a")
    msgs_b = orchestrator.short_term.get("user-b")
    assert any("علی" in (m.content or "") for m in msgs_a)
    assert any("سارا" in (m.content or "") for m in msgs_b)
    assert not any("سارا" in (m.content or "") for m in msgs_a)


def test_chat_endpoint_with_mock(client):
    r = client.post("/api/v1/chat", json={"message": "Hello agent", "session_id": "api-e2e"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("completed", "needs_approval", "error")
    assert "run_id" in data
    assert "response" in data


def test_pending_approvals_endpoint(client):
    r = client.get("/api/v1/approvals/pending")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_tool_rejects_missing_required_args():
    result = await tool_registry.execute("search_web", {})
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_tool_rejects_invalid_types():
    result = await tool_registry.execute("search_web", {"query": "ok", "max_results": "not-an-int"})
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_tool_accepts_valid_args():
    result = await tool_registry.execute("search_web", {"query": "hello world", "max_results": 3})
    assert result.success is True
    assert result.data is not None
