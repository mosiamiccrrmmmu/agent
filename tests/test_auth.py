"""LocalAuth enforcement tests."""

from __future__ import annotations

import os

os.environ["SECRET_KEY"] = "test-secret-key-at-least-16-chars"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_auth.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test_auth.db"
os.environ["DEFAULT_LLM_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "development"

from app.config.settings import get_settings
from app.desktop.auth import LocalAuth
from app.desktop.secrets import SecureSecretStore
from app.main import create_app
from fastapi.testclient import TestClient


def test_chat_rejects_missing_token(tmp_path, monkeypatch):
    os.environ["REQUIRE_LOCAL_AUTH"] = "true"
    get_settings.cache_clear()

    from app.desktop import paths as paths_mod

    monkeypatch.setattr(paths_mod, "_default_root", lambda: tmp_path / "pai")

    store = SecureSecretStore(prefer_keyring=False)
    store.set("local_api_token", "expected-token-value-xyz")
    auth = LocalAuth(store=store)

    import app.api.routes as routes_mod
    import app.desktop.auth as auth_mod

    monkeypatch.setattr(auth_mod, "local_auth", auth)
    monkeypatch.setattr(routes_mod, "local_auth", auth)

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/api/v1/chat", json={"message": "hi"})
        assert r.status_code == 401, r.text

        r2 = client.post(
            "/api/v1/chat",
            json={"message": "hi"},
            headers={"X-Personal-Ai-Token": "wrong"},
        )
        assert r2.status_code == 401

        r3 = client.post(
            "/api/v1/chat",
            json={"message": "hi"},
            headers={"X-Personal-Ai-Token": "expected-token-value-xyz"},
        )
        assert r3.status_code != 401

    os.environ["REQUIRE_LOCAL_AUTH"] = "false"
    get_settings.cache_clear()


def test_health_public():
    os.environ["REQUIRE_LOCAL_AUTH"] = "true"
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
    os.environ["REQUIRE_LOCAL_AUTH"] = "false"
    get_settings.cache_clear()
