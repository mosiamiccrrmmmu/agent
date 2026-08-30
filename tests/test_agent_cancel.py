import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_cancel.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test_cancel.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")

from app.agent.orchestrator import (
    clear_agent_cancel,
    is_agent_cancelled,
    request_agent_cancel,
)


def test_cancel_flags():
    clear_agent_cancel()
    assert is_agent_cancelled() is False
    request_agent_cancel()
    assert is_agent_cancelled() is True
    clear_agent_cancel()
    assert is_agent_cancelled() is False
