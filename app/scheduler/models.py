"""Scheduled task models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ScheduleKind(StrEnum):
    ONE_TIME = "one_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    CRON = "cron"
    INTERVAL = "interval"


class ScheduledTaskStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = "default"
    name: str
    prompt: str
    kind: ScheduleKind = ScheduleKind.ONE_TIME
    run_at: datetime | None = None
    time_of_day: str | None = None
    cron: str | None = None
    interval_seconds: int | None = None
    timezone: str = "Asia/Tehran"
    status: ScheduledTaskStatus = ScheduledTaskStatus.ACTIVE
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
