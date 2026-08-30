"""Scheduler with SQLite-persisted tasks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.database.sqlite_store import SQLiteStore, get_store
from app.scheduler.models import ScheduledTask, ScheduledTaskStatus, ScheduleKind

logger = get_logger(__name__)

TaskHandler = Callable[[ScheduledTask], Awaitable[None]]


class Scheduler:
    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_store()
        self._handler: TaskHandler | None = None
        self._loaded = False

    def set_handler(self, handler: TaskHandler) -> None:
        self._handler = handler

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True

    def add(self, task: ScheduledTask) -> ScheduledTask:
        self._ensure_loaded()
        if task.kind == ScheduleKind.ONE_TIME and task.run_at:
            task.next_run_at = task.run_at
        elif task.kind == ScheduleKind.DAILY and task.time_of_day:
            task.next_run_at = self._next_daily(task.time_of_day)
        elif task.kind == ScheduleKind.INTERVAL and task.interval_seconds:
            task.next_run_at = datetime.utcnow() + timedelta(seconds=task.interval_seconds)
        self._store.task_save(task.model_dump(mode="json"))
        logger.info(
            "scheduled_task_added", task_id=task.id, name=task.name, kind=task.kind.value
        )
        return task

    def _next_daily(self, time_of_day: str) -> datetime:
        hour, minute = map(int, time_of_day.split(":"))
        now = datetime.utcnow()
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    def list_tasks(self, user_id: str | None = None) -> list[ScheduledTask]:
        rows = self._store.task_list(user_id)
        return [ScheduledTask(**r) for r in rows]

    def cancel(self, task_id: str) -> bool:
        row = self._store.task_get(task_id)
        if not row:
            return False
        task = ScheduledTask(**row)
        task.status = ScheduledTaskStatus.CANCELLED
        self._store.task_save(task.model_dump(mode="json"))
        return True

    def due_tasks(self, now: datetime | None = None) -> list[ScheduledTask]:
        now = now or datetime.utcnow()
        return [
            t
            for t in self.list_tasks()
            if t.status == ScheduledTaskStatus.ACTIVE
            and t.next_run_at is not None
            and t.next_run_at <= now
        ]

    async def tick(self) -> int:
        if not self._handler:
            return 0
        due = self.due_tasks()
        for task in due:
            try:
                await self._handler(task)
                task.last_run_at = datetime.utcnow()
                if task.kind == ScheduleKind.ONE_TIME:
                    task.status = ScheduledTaskStatus.COMPLETED
                    task.next_run_at = None
                elif task.kind == ScheduleKind.DAILY and task.time_of_day:
                    task.next_run_at = self._next_daily(task.time_of_day)
                elif task.kind == ScheduleKind.INTERVAL and task.interval_seconds:
                    task.next_run_at = datetime.utcnow() + timedelta(
                        seconds=task.interval_seconds
                    )
                self._store.task_save(task.model_dump(mode="json"))
            except Exception as exc:
                logger.exception("scheduled_task_failed", task_id=task.id)
                task.status = ScheduledTaskStatus.FAILED
                task.metadata["last_error"] = str(exc)
                self._store.task_save(task.model_dump(mode="json"))
        return len(due)


scheduler = Scheduler()
