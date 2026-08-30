import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./t.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./t.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.agent.cancel import clear_agent_cancel, request_agent_cancel
from app.agent.orchestrator import AgentOrchestrator
from app.core.execution_gate import is_blocked, reset_gate
from app.main import create_app


@pytest.fixture(autouse=True)
def _clear_gates():
    clear_agent_cancel()
    reset_gate()
    yield
    clear_agent_cancel()
    reset_gate()


def test_stop_all_blocks_new_agent_runs():
    client = TestClient(create_app())
    r = client.post("/api/v1/desktop/stop-all")
    assert r.status_code == 200
    assert is_blocked() is True

    async def _run():
        orch = AgentOrchestrator()
        return await orch.run("hello", session_id="gate-test")

    result = asyncio.run(_run())
    assert result.status == "cancelled"
    assert result.error in ("BLOCKED", "CANCELLED")

    r2 = client.post("/api/v1/desktop/reset-stop")
    assert r2.status_code == 200
    assert is_blocked() is False


@pytest.mark.asyncio
async def test_automation_engine_cancel_skips_rest():
    from app.automation.engine import AutomationEngine

    eng = AutomationEngine()
    wf = eng.create(
        "t",
        [
            {"action": "WAIT", "arguments": {}},
            {"action": "FILE_COPY", "arguments": {"src": "a", "dst": "b"}},
        ],
    )
    calls: list[str] = []

    async def executor(action, args):
        calls.append(action)
        if action == "WAIT":
            request_agent_cancel()
        return {"success": True}

    out = await eng.run(wf.workflow_id, executor)
    assert out.status.value == "CANCELLED"
    assert calls == ["WAIT"]
