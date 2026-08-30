"""Formal Agent run lifecycle — invalid transitions are rejected."""

from __future__ import annotations

from enum import StrEnum


class AgentState(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


_TRANSITIONS: dict[AgentState, frozenset[AgentState]] = {
    AgentState.IDLE: frozenset(
        {AgentState.PLANNING, AgentState.RUNNING, AgentState.CANCELLED}
    ),
    AgentState.PLANNING: frozenset(
        {
            AgentState.RUNNING,
            AgentState.WAITING_APPROVAL,
            AgentState.FAILED,
            AgentState.CANCELLED,
            AgentState.TIMEOUT,
            AgentState.CANCELLING,
        }
    ),
    AgentState.RUNNING: frozenset(
        {
            AgentState.WAITING_APPROVAL,
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.TIMEOUT,
            AgentState.PAUSED,
            AgentState.CANCELLING,
            AgentState.CANCELLED,
        }
    ),
    AgentState.WAITING_APPROVAL: frozenset(
        {
            AgentState.RUNNING,
            AgentState.CANCELLED,
            AgentState.FAILED,
            AgentState.TIMEOUT,
            AgentState.CANCELLING,
        }
    ),
    AgentState.PAUSED: frozenset(
        {AgentState.RUNNING, AgentState.CANCELLED, AgentState.CANCELLING}
    ),
    AgentState.CANCELLING: frozenset({AgentState.CANCELLED, AgentState.FAILED}),
    AgentState.CANCELLED: frozenset(),
    AgentState.COMPLETED: frozenset(),
    AgentState.FAILED: frozenset(),
    AgentState.TIMEOUT: frozenset(),
}


class InvalidTransitionError(ValueError):
    pass


class AgentLifecycle:
    def __init__(self, initial: AgentState = AgentState.IDLE) -> None:
        self.state = initial

    def can_transition(self, to: AgentState) -> bool:
        return to in _TRANSITIONS.get(self.state, frozenset())

    def transition(self, to: AgentState) -> AgentState:
        if not self.can_transition(to):
            raise InvalidTransitionError(
                f"Illegal transition {self.state.value} -> {to.value}"
            )
        self.state = to
        return self.state

    @property
    def is_terminal(self) -> bool:
        return self.state in (
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.CANCELLED,
            AgentState.TIMEOUT,
        )
