import asyncio
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./t.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./t.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")

from app.config.settings import get_settings
from app.llm.base import Message, MessageRole
from app.llm.local import LocalProvider
from app.llm.router import ModelRouter, RouteReason


def test_router_default_mock():
    get_settings.cache_clear()
    r = ModelRouter()
    d = r.decide(preferred="mock")
    assert d.provider_name == "mock"


def test_router_offline_local():
    r = ModelRouter()
    d = r.decide(offline=True)
    assert d.provider_name == "local"
    assert d.reason == RouteReason.OFFLINE


def test_local_provider_generate():
    async def _run():
        p = LocalProvider()
        resp = await p.generate([Message(role=MessageRole.USER, content="hi")])
        assert "LOCAL_AI_UNAVAILABLE" in (resp.content or "")

    asyncio.run(_run())
