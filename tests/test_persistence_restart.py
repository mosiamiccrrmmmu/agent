"""Restart durability tests — write, drop in-memory objects, reload from SQLite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_persist.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test_persist.db")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "mock")
os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")

from app.database.sqlite_store import reset_store_for_tests
from app.llm.base import Message, MessageRole
from app.memory.long_term import LongTermMemory
from app.memory.profile import ProfileStore
from app.memory.short_term import ShortTermMemory
from app.permissions.manager import PermissionManager
from app.permissions.models import ApprovalStatus
from app.scheduler.engine import Scheduler
from app.scheduler.models import ScheduleKind, ScheduledTask
from app.tools.base import RiskLevel


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "rc2_persist.db"


def test_long_term_memory_survives_reload(db_path: Path):
    store = reset_store_for_tests(db_path)
    mem = LongTermMemory(store=store)
    item = mem.add("I prefer short messages", category="preference")
    item_id = item.id

    # Simulate restart: new objects, same DB file
    store2 = reset_store_for_tests.__wrapped__(db_path) if False else None  # noqa
    from app.database.sqlite_store import SQLiteStore

    store2 = SQLiteStore(db_path=db_path)
    mem2 = LongTermMemory(store=store2)
    found = mem2.get(item_id)
    assert found is not None
    assert found.content == "I prefer short messages"
    assert any(m.content == "I prefer short messages" for m in mem2.list())


def test_conversation_survives_reload(db_path: Path):
    store = reset_store_for_tests(db_path)
    stm = ShortTermMemory(store=store)
    stm.add("sess-1", Message(role=MessageRole.USER, content="hello persist"))
    stm.add("sess-1", Message(role=MessageRole.ASSISTANT, content="hi back"))

    from app.database.sqlite_store import SQLiteStore

    store2 = SQLiteStore(db_path=db_path)
    stm2 = ShortTermMemory(store=store2)
    msgs = stm2.get("sess-1")
    assert len(msgs) >= 2
    assert msgs[0].content == "hello persist"
    assert msgs[1].content == "hi back"


def test_profile_survives_reload(db_path: Path):
    store = reset_store_for_tests(db_path)
    ps = ProfileStore(store=store)
    ps.update("u1", name="Ali", language="fa")

    from app.database.sqlite_store import SQLiteStore

    store2 = SQLiteStore(db_path=db_path)
    ps2 = ProfileStore(store=store2)
    p = ps2.get("u1")
    assert p.name == "Ali"
    assert p.language == "fa"


def test_approval_survives_reload_and_consume(db_path: Path):
    store = reset_store_for_tests(db_path)
    pm = PermissionManager(store=store)
    args = {"chat_id": "Ali", "body": "hello"}
    d = pm.check("send_whatsapp", RiskLevel.HIGH, args, user_id="u1")
    aid = d.approval_request.id
    pm.resolve(aid, ApprovalStatus.APPROVED)

    from app.database.sqlite_store import SQLiteStore

    store2 = SQLiteStore(db_path=db_path)
    pm2 = PermissionManager(store=store2)
    req = pm2.get_pending(aid)
    assert req is not None
    assert req.status == ApprovalStatus.APPROVED
    assert req.action_hash
    ok, reason = pm2.consume(aid, "send_whatsapp", args)
    assert ok is True
    ok2, reason2 = pm2.consume(aid, "send_whatsapp", args)
    assert ok2 is False
    assert reason2 == "approval_already_consumed"


def test_scheduler_survives_reload(db_path: Path):
    store = reset_store_for_tests(db_path)
    sch = Scheduler(store=store)
    task = ScheduledTask(
        name="morning briefing",
        prompt="What do I have today?",
        kind=ScheduleKind.DAILY,
        time_of_day="08:00",
        user_id="u1",
    )
    created = sch.add(task)
    tid = created.id

    from app.database.sqlite_store import SQLiteStore

    store2 = SQLiteStore(db_path=db_path)
    sch2 = Scheduler(store=store2)
    tasks = sch2.list_tasks("u1")
    assert any(t.id == tid and t.name == "morning briefing" for t in tasks)
