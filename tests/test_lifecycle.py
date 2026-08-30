import pytest

from app.agent.lifecycle import AgentLifecycle, AgentState, InvalidTransitionError


def test_happy_path():
    life = AgentLifecycle()
    life.transition(AgentState.PLANNING)
    life.transition(AgentState.RUNNING)
    life.transition(AgentState.COMPLETED)
    assert life.is_terminal


def test_illegal_transition():
    life = AgentLifecycle(AgentState.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        life.transition(AgentState.RUNNING)


def test_cancel_path():
    life = AgentLifecycle()
    life.transition(AgentState.RUNNING)
    life.transition(AgentState.CANCELLING)
    life.transition(AgentState.CANCELLED)
    assert life.state == AgentState.CANCELLED
