"""Memory unit tests."""

from app.llm.base import Message, MessageRole
from app.memory.long_term import LongTermMemory
from app.memory.short_term import ShortTermMemory


def test_short_term():
    stm = ShortTermMemory()
    stm.add("s1", Message(role=MessageRole.USER, content="hello"))
    stm.add("s1", Message(role=MessageRole.ASSISTANT, content="hi"))
    msgs = stm.get("s1")
    assert len(msgs) == 2
    assert msgs[0].content == "hello"


def test_long_term():
    ltm = LongTermMemory()
    item = ltm.add("User prefers Persian", category="preference")
    assert item.id
    found = ltm.search("Persian")
    assert len(found) == 1
    assert ltm.delete(item.id) is True
    assert ltm.get(item.id).active is False
