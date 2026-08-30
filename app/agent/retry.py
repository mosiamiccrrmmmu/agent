"""Retry policy — only for explicitly retryable failures."""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Awaitable, Callable, TypeVar

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryPolicy(StrEnum):
    NO_RETRY = "no_retry"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


NON_RETRYABLE = frozenset(
    {
        "PERMISSION_DENIED",
        "APPROVAL_DENIED",
        "APPROVAL_REQUIRED",
        "VALIDATION_ERROR",
        "INVALID_ARGUMENTS",
        "SECURITY_VIOLATION",
        "NOT_CONFIGURED",
        "APP_NOT_ALLOWLISTED",
    }
)


def is_retryable_error(code: str | None) -> bool:
    if not code:
        return False
    upper = code.upper()
    if upper in NON_RETRYABLE:
        return False
    return any(
        x in upper
        for x in ("TIMEOUT", "NETWORK", "RATE_LIMIT", "429", "503", "TEMPORARY")
    )


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy = RetryPolicy.EXPONENTIAL,
    max_attempts: int = 3,
    base_delay: float = 0.25,
    error_code: str | None = None,
) -> T:
    if policy == RetryPolicy.NO_RETRY or max_attempts <= 1:
        return await fn()
    if error_code and not is_retryable_error(error_code):
        return await fn()

    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            delay = (
                base_delay
                if policy == RetryPolicy.FIXED
                else base_delay * (2 ** (attempt - 1))
            )
            logger.warning(
                "retry_attempt",
                attempt=attempt,
                delay=delay,
                error=type(exc).__name__,
            )
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc
