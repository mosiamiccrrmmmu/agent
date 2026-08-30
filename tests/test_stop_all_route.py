import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./t.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./t.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")

from fastapi.testclient import TestClient

from app.agent.cancel import clear_agent_cancel, is_agent_cancelled
from app.main import create_app


def test_stop_all_sets_cancel_flag():
    clear_agent_cancel()
    client = TestClient(create_app())
    r = client.post("/api/v1/desktop/stop-all")
    assert r.status_code == 200
    assert r.json().get("status") == "stopped"
    assert is_agent_cancelled() is True
    clear_agent_cancel()
