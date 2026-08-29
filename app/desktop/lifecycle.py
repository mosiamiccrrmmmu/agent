"""Backend lifecycle for the desktop shell.

Start → health → init agent → ready
Shutdown → stop tasks → flush logs → close connections
Crash recovery with restart_limit + backoff.
"""

from __future__ import annotations

import asyncio
import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.desktop.paths import get_app_paths

logger = get_logger(__name__)


class LifecycleState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    CRASHED = "crashed"


class LifecycleStatus(BaseModel):
    state: LifecycleState = LifecycleState.STOPPED
    backend_healthy: bool = False
    database_ok: bool = False
    restarts: int = 0
    last_error: str | None = None
    started_at: float | None = None
    version: str = "1.0.0"


class BackendLifecycle:
    def __init__(
        self,
        *,
        max_restarts: int = 5,
        backoff_base_seconds: float = 1.0,
        health_timeout_seconds: float = 5.0,
    ) -> None:
        self.max_restarts = max_restarts
        self.backoff_base = backoff_base_seconds
        self.health_timeout = health_timeout_seconds
        self.status = LifecycleStatus()
        self.paths = get_app_paths()

    def mark_starting(self) -> None:
        self.status.state = LifecycleState.STARTING
        self.status.started_at = time.time()
        self.status.last_error = None
        logger.info("backend_starting", paths=str(self.paths.root))

    def mark_ready(self, *, database_ok: bool = True) -> None:
        self.status.state = LifecycleState.READY
        self.status.backend_healthy = True
        self.status.database_ok = database_ok
        logger.info("backend_ready")

    def mark_crashed(self, error: str) -> None:
        self.status.state = LifecycleState.CRASHED
        self.status.backend_healthy = False
        self.status.last_error = error[:500]
        logger.error("backend_crashed", error=error[:200])

    def mark_stopping(self) -> None:
        self.status.state = LifecycleState.STOPPING
        logger.info("backend_stopping")

    def mark_stopped(self) -> None:
        self.status.state = LifecycleState.STOPPED
        self.status.backend_healthy = False
        logger.info("backend_stopped")

    def can_restart(self) -> bool:
        return self.status.restarts < self.max_restarts

    def record_restart(self) -> float:
        self.status.restarts += 1
        delay = self.backoff_base * (2 ** min(self.status.restarts - 1, 4))
        logger.warning("backend_restart_scheduled", attempt=self.status.restarts, delay=delay)
        return delay

    async def wait_healthy(self, check_fn: Any, attempts: int = 20) -> bool:
        for i in range(attempts):
            try:
                ok = await check_fn()
                if ok:
                    return True
            except Exception as exc:
                logger.debug("health_check_failed", attempt=i, error=str(exc))
            await asyncio.sleep(0.25)
        return False

    def snapshot(self) -> dict[str, Any]:
        return self.status.model_dump()


lifecycle = BackendLifecycle()
