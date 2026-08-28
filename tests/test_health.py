"""Basic health and structure tests."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://agent:agent@localhost:5432/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://agent:agent@localhost:5432/test")

from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_list_tools(client):
    resp = client.get("/api/v1/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert isinstance(tools, list)
    names = [t["name"] for t in tools]
    assert "search_web" in names
    assert "remember" in names
    assert "recall" in names
