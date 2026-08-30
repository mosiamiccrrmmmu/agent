"""Process-local agent cancellation (STOP)."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)

_GLOBAL_CANCEL = False


def request_agent_cancel() -> None:
    global _GLOBAL_CANCEL
    _GLOBAL_CANCEL = True
    logger.warning("agent_cancel_requested")


def clear_agent_cancel() -> None:
    global _GLOBAL_CANCEL
    _GLOBAL_CANCEL = False


def is_agent_cancelled() -> bool:
    return _GLOBAL_CANCEL
