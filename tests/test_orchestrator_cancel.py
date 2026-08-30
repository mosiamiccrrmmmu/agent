import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./t.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./t.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")

import pytest

from app.agent.cancel import clear_agent_cancel, request_agent_cancel
from app.agent.orchestrator import AgentOrchestrator
from app.llm.base import LLMResponse, LLMUsage, ToolCall


class _StickyToolLLM:
    name = "sticky"

    async def generate(
        self, messages, model=None, tools=None, temperature=0.2, max_tokens=None
    ):
        return LLMResponse(
            content="",
            model="sticky",
            usage=LLMUsage(input_tokens=1, output_tokens=1, total_tokens=2),
            tool_calls=[
                ToolCall(id="1", name="memory_recall", arguments={"query": "x"})
            ],
        )

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_orchestrator_cancels_mid_loop(monkeypatch):
    clear_agent_cancel()
    from app.llm import factory as fac

    sticky = _StickyToolLLM()
    monkeypatch.setattr(
        fac.llm_factory,
        "resolve_model",
        lambda task_type=None: (sticky, "sticky"),
    )

    orch = AgentOrchestrator()
    request_agent_cancel()
    result = await orch.run(
        "do something with tools", session_id="cancel-test", max_steps=5
    )
    assert result.status == "cancelled"
    assert result.error == "CANCELLED"
    clear_agent_cancel()
