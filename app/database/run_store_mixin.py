"""Agent run persistence methods mixed onto SQLiteStore."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.database.sqlite_store import SQLiteStore


def attach_run_methods(cls: type) -> type:
    def upsert_agent_run(
        self: SQLiteStore,
        run_id: str,
        *,
        session_id: str = "default",
        user_id: str = "default",
        status: str,
        goal: str = "",
        plan: dict | None = None,
        current_step: int = 0,
        error: str | None = None,
        metadata: dict | None = None,
        started: bool = False,
        finished: bool = False,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._tx() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL DEFAULT 'default',
                    user_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    goal TEXT NOT NULL DEFAULT '',
                    plan_json TEXT NOT NULL DEFAULT '{}',
                    current_step INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )"""
            )
            row = conn.execute(
                "SELECT run_id FROM agent_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                conn.execute(
                    """INSERT INTO agent_runs
                    (run_id, session_id, user_id, created_at, started_at, finished_at,
                     status, goal, plan_json, current_step, error, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        session_id,
                        user_id,
                        now,
                        now if started else None,
                        now if finished else None,
                        status,
                        goal,
                        json.dumps(plan or {}),
                        current_step,
                        error,
                        json.dumps(metadata or {}),
                    ),
                )
            else:
                sets = [
                    "status = ?",
                    "current_step = ?",
                    "goal = ?",
                    "plan_json = ?",
                    "error = ?",
                    "metadata_json = ?",
                ]
                args: list = [
                    status,
                    current_step,
                    goal,
                    json.dumps(plan or {}),
                    error,
                    json.dumps(metadata or {}),
                ]
                if started:
                    sets.append("started_at = COALESCE(started_at, ?)")
                    args.append(now)
                if finished:
                    sets.append("finished_at = ?")
                    args.append(now)
                args.append(run_id)
                conn.execute(
                    f"UPDATE agent_runs SET {', '.join(sets)} WHERE run_id = ?",
                    args,
                )

    def get_agent_run(self: SQLiteStore, run_id: str) -> dict | None:
        with self._tx() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL DEFAULT 'default',
                    user_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    goal TEXT NOT NULL DEFAULT '',
                    plan_json TEXT NOT NULL DEFAULT '{}',
                    current_step INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )"""
            )
            row = conn.execute(
                "SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def list_agent_runs(
        self: SQLiteStore, session_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        with self._tx() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL DEFAULT 'default',
                    user_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    goal TEXT NOT NULL DEFAULT '',
                    plan_json TEXT NOT NULL DEFAULT '{}',
                    current_step INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )"""
            )
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM agent_runs WHERE session_id = ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def mark_stale_running_runs(self: SQLiteStore) -> int:
        with self._tx() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL DEFAULT 'default',
                    user_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    goal TEXT NOT NULL DEFAULT '',
                    plan_json TEXT NOT NULL DEFAULT '{}',
                    current_step INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )"""
            )
            cur = conn.execute(
                """UPDATE agent_runs SET status = 'failed',
                   error = 'recovered_after_restart', finished_at = ?
                   WHERE status IN ('running', 'planning', 'cancelling')""",
                (datetime.utcnow().isoformat(),),
            )
            return cur.rowcount

    cls.upsert_agent_run = upsert_agent_run  # type: ignore[attr-defined]
    cls.get_agent_run = get_agent_run  # type: ignore[attr-defined]
    cls.list_agent_runs = list_agent_runs  # type: ignore[attr-defined]
    cls.mark_stale_running_runs = mark_stale_running_runs  # type: ignore[attr-defined]
    return cls
