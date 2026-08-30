"""Memory unit tests."""

from pathlib import Path

from app.database.sqlite_store import reset_store_for_tests
from app.llm.base import Message, MessageRole
from app.memory.long_term import LongTermMemory
from app.memory.short_term import ShortTermMemory


def test_short_term(tmp_path: Path):
    store = reset_store_for_tests(tmp_path / "mem_st.db")
    stm = ShortTermMemory(store=store)
    stm.add("s1", Message(role=MessageRole.USER, content="hello"))
    stm.add("s1", Message(role=MessageRole.ASSISTANT, content="hi"))
    msgs = stm.get("s1")
    assert len(msgs) == 2
    assert msgs[0].content == "hello"


def test_long_term(tmp_path: Path):
    store = reset_store_for_tests(tmp_path / "mem_lt.db")
    ltm = LongTermMemory(store=store)
    item = ltm.add("User prefers Persian", category="preference")
    assert item.id
    found = ltm.search("Persian")
    assert len(found) == 1
    assert ltm.delete(item.id) is True
    assert ltm.get(item.id).active is False
