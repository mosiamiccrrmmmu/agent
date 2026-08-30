"""Unit tests for Grok provider wiring — no real API key required."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_grok.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test_grok.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")
os.environ.setdefault("APP_ENV", "development")

from app.config.settings import Settings, get_settings
from app.llm.factory import LLMFactory, TaskType
from app.llm.grok import GrokProvider
from app.llm.mock import MockLLMProvider


def test_settings_supports_grok_provider():
    get_settings.cache_clear()
    s = Settings(
        secret_key="test-secret-key-at-least-16-chars",
        default_llm_provider="grok",
        xai_api_key="xai-test-key-12345678",
    )
    assert s.default_llm_provider == "grok"
    assert s.effective_xai_api_key == "xai-test-key-12345678"
    assert s.app_version == "1.0.0"
    get_settings.cache_clear()


def test_settings_grok_api_key_alias():
    get_settings.cache_clear()
    s = Settings(
        secret_key="test-secret-key-at-least-16-chars",
        grok_api_key="grok-alias-key-999",
    )
    assert s.effective_xai_api_key == "grok-alias-key-999"
    get_settings.cache_clear()


def test_factory_registers_grok():
    factory = LLMFactory()
    get_settings.cache_clear()
    os.environ["XAI_API_KEY"] = "xai-unit-test-key-abcdef"
    os.environ["DEFAULT_LLM_PROVIDER"] = "grok"
    get_settings.cache_clear()
    try:
        provider = factory.get_provider("grok")
        assert provider.name == "grok"
        assert isinstance(provider, GrokProvider)
    finally:
        factory.clear()
        os.environ.pop("XAI_API_KEY", None)
        os.environ["DEFAULT_LLM_PROVIDER"] = "mock"
        get_settings.cache_clear()


def test_factory_grok_missing_key_raises():
    factory = LLMFactory()
    get_settings.cache_clear()
    os.environ.pop("XAI_API_KEY", None)
    os.environ.pop("GROK_API_KEY", None)
    os.environ["DEFAULT_LLM_PROVIDER"] = "mock"
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="XAI_API_KEY"):
        factory.get_provider("grok")
    factory.clear()


def test_factory_unknown_provider():
    factory = LLMFactory()
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        factory.get_provider("not-a-provider")


def test_factory_mock_and_resolve_model():
    factory = LLMFactory()
    factory.register_provider("mock", MockLLMProvider())
    provider, model = factory.resolve_model(TaskType.GENERAL, "mock")
    assert provider.name == "mock"
    assert model == "mock-model"
    factory.clear()


def test_grok_provider_requires_api_key():
    with pytest.raises(ValueError, match="required"):
        GrokProvider(api_key="")


def test_grok_tool_definition_shape():
    """Grok uses OpenAI-compatible tool schema."""
    from app.llm.base import ToolDefinition

    td = ToolDefinition(
        name="search_web",
        description="Search",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
    )
    provider = GrokProvider(api_key="xai-shape-test-key-xx")
    converted = provider._convert_tools([td])
    assert converted is not None
    assert converted[0]["type"] == "function"
    assert converted[0]["function"]["name"] == "search_web"
