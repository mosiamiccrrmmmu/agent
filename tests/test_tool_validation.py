"""Strict Pydantic validation for tool arguments."""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://agent:agent@localhost:5432/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://agent:agent@localhost:5432/test")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")

import pytest

from app.tools.memory_tools import RecallTool, RememberTool
from app.tools.registry import ToolRegistry
from app.tools.web.search import WebSearchTool


@pytest.mark.asyncio
async def test_web_search_rejects_empty_query():
    tool = WebSearchTool()
    with pytest.raises(ValueError):
        tool.validate_arguments({"query": ""})


@pytest.mark.asyncio
async def test_web_search_rejects_missing_query():
    tool = WebSearchTool()
    with pytest.raises(ValueError):
        tool.validate_arguments({})


@pytest.mark.asyncio
async def test_web_search_accepts_valid():
    tool = WebSearchTool()
    validated = tool.validate_arguments({"query": "hello world", "max_results": 3})
    assert validated["query"] == "hello world"
    assert validated["max_results"] == 3


@pytest.mark.asyncio
async def test_registry_returns_error_on_invalid_args():
    reg = ToolRegistry()
    reg.register(WebSearchTool())
    result = await reg.execute("search_web", {"query": ""})
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_remember_rejects_empty_content():
    tool = RememberTool()
    with pytest.raises(ValueError):
        tool.validate_arguments({"content": ""})


@pytest.mark.asyncio
async def test_recall_accepts_valid():
    tool = RecallTool()
    validated = tool.validate_arguments({"query": "name"})
    assert validated["query"] == "name"
