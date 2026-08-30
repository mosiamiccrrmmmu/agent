"""File sandbox — path traversal blocked, CRUD inside roots."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_fs.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test_fs.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")

import pytest

from app.tools.files.sandbox import PathSandbox, PathSandboxError
from app.tools.files.tools import DeleteFileTool, ListFilesTool, ReadFileTool, WriteFileTool


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch):
    root = tmp_path / "sandbox_root"
    root.mkdir()
    sb = PathSandbox(roots=[root])
    import app.tools.files.tools as ft

    monkeypatch.setattr(ft, "_sandbox", sb)
    return root


@pytest.mark.asyncio
async def test_write_read_list(sandbox: Path):
    w = WriteFileTool()
    r = await w.execute(path="notes/hello.txt", content="hello")
    assert r.success
    rd = ReadFileTool()
    out = await rd.execute(path="notes/hello.txt")
    assert out.success
    assert out.data["content"] == "hello"
    ls = ListFilesTool()
    listing = await ls.execute(path="notes")
    assert listing.success
    assert any(e["name"] == "hello.txt" for e in listing.data["entries"])


@pytest.mark.asyncio
async def test_path_traversal_blocked(sandbox: Path):
    rd = ReadFileTool()
    out = await rd.execute(path="../../etc/passwd")
    assert out.success is False


@pytest.mark.asyncio
async def test_delete_high_risk_but_works_when_called(sandbox: Path):
    await WriteFileTool().execute(path="gone.txt", content="x")
    d = DeleteFileTool()
    assert d.metadata.risk_level.value == "high"
    out = await d.execute(path="gone.txt")
    assert out.success
    assert not (sandbox / "gone.txt").exists()


def test_sandbox_rejects_absolute_outside(tmp_path: Path):
    root = tmp_path / "r"
    root.mkdir()
    sb = PathSandbox(roots=[root])
    with pytest.raises(PathSandboxError):
        sb.resolve("/etc/passwd")
