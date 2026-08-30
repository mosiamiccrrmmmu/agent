"""SQLite persistence for desktop Personal AI.

Data lives under %LOCALAPPDATA%\\PersonalAI\\database (or XDG on Linux).
All production durable state goes through this module — not process memory alone.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from app.desktop.paths import get_app_paths

SCHEMA_VERSION = 2

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS long_term_memory (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    source TEXT NOT NULL DEFAULT 'user',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ltm_active ON long_term_memory(active);
CREATE INDEX IF NOT EXISTS idx_ltm_category ON long_term_memory(category);

CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    name TEXT,
    tool_calls_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id, id);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    details_json TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    action_hash TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'default',
    session_id TEXT NOT NULL DEFAULT 'default',
    status TEXT NOT NULL,
    message_to_user TEXT NOT NULL DEFAULT '',
    edited_payload_json TEXT,
    consumed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

CREATE TABLE IF NOT EXISTS agent_runs (
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
);
CREATE INDEX IF NOT EXISTS idx_runs_session ON agent_runs(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_runs_status ON agent_runs(status);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    kind TEXT NOT NULL,
    run_at TEXT,
    time_of_day TEXT,
    cron TEXT,
    interval_seconds INTEGER,
    timezone TEXT NOT NULL DEFAULT 'Asia/Tehran',
    status TEXT NOT NULL,
    last_run_at TEXT,
    next_run_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON scheduled_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_next ON scheduled_tasks(next_run_at);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _dt(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class SQLiteStore:
    """Thread-safe SQLite access for desktop persistence."""

    def __init__(self, db_path: Path | None = None) -> None:
        paths = get_app_paths()
        self.db_path = db_path or (paths.database / "personal_ai.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self._connect()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._tx() as conn:
            conn.executescript(SCHEMA_SQL)
            row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO meta(key, value) VALUES ('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )

    def ltm_add(
        self,
        item_id: str,
        content: str,
        category: str = "general",
        source: str = "user",
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        now = datetime.utcnow()
        with self._tx() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO long_term_memory
                   (id, content, category, source, metadata_json, active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                (
                    item_id,
                    content,
                    category,
                    source,
                    json.dumps(metadata or {}),
                    _dt(created_at or now),
                    _dt(updated_at or now),
                ),
            )

    def ltm_list(self, category: str | None = None, active_only: bool = True) -> list[dict[str, Any]]:
        with self._tx() as conn:
            q = "SELECT * FROM long_term_memory WHERE 1=1"
            params: list[Any] = []
            if active_only:
                q += " AND active=1"
            if category:
                q += " AND category=?"
                params.append(category)
            q += " ORDER BY created_at DESC"
            rows = conn.execute(q, params).fetchall()
        return [self._ltm_row(r) for r in rows]

    def ltm_get(self, item_id: str) -> dict[str, Any] | None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT * FROM long_term_memory WHERE id=?", (item_id,)
            ).fetchone()
        return self._ltm_row(row) if row else None

    def ltm_update(self, item_id: str, **fields: Any) -> bool:
        item = self.ltm_get(item_id)
        if not item:
            return False
        content = fields.get("content", item["content"])
        category = fields.get("category", item["category"])
        active = fields.get("active", item["active"])
        meta = fields.get("metadata", item["metadata"])
        with self._tx() as conn:
            conn.execute(
                """UPDATE long_term_memory
                   SET content=?, category=?, metadata_json=?, active=?, updated_at=?
                   WHERE id=?""",
                (
                    content,
                    category,
                    json.dumps(meta),
                    1 if active else 0,
                    _dt(datetime.utcnow()),
                    item_id,
                ),
            )
        return True

    def ltm_delete(self, item_id: str) -> bool:
        return self.ltm_update(item_id, active=False)

    def ltm_search(self, query: str) -> list[dict[str, Any]]:
        q = f"%{query.lower()}%"
        with self._tx() as conn:
            rows = conn.execute(
                """SELECT * FROM long_term_memory
                   WHERE active=1 AND lower(content) LIKE ?
                   ORDER BY created_at DESC""",
                (q,),
            ).fetchall()
        return [self._ltm_row(r) for r in rows]

    @staticmethod
    def _ltm_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "content": row["content"],
            "category": row["category"],
            "source": row["source"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "active": bool(row["active"]),
            "created_at": _parse_dt(row["created_at"]),
            "updated_at": _parse_dt(row["updated_at"]),
        }

    def profile_get(self, user_id: str) -> dict[str, Any] | None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT data_json FROM profiles WHERE user_id=?", (user_id,)
            ).fetchone()
        if not row:
            return None
        return json.loads(row["data_json"])

    def profile_set(self, user_id: str, data: dict[str, Any]) -> None:
        with self._tx() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO profiles(user_id, data_json, updated_at)
                   VALUES (?, ?, ?)""",
                (user_id, json.dumps(data, default=str), _dt(datetime.utcnow())),
            )

    def conversation_append(
        self,
        session_id: str,
        role: str,
        content: str | None = None,
        tool_call_id: str | None = None,
        name: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        with self._tx() as conn:
            conn.execute(
                """INSERT INTO conversations
                   (session_id, role, content, tool_call_id, name, tool_calls_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    role,
                    content,
                    tool_call_id,
                    name,
                    json.dumps(tool_calls) if tool_calls else None,
                    _dt(datetime.utcnow()),
                ),
            )

    def conversation_get(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._tx() as conn:
            rows = conn.execute(
                """SELECT * FROM conversations WHERE session_id=?
                   ORDER BY id DESC LIMIT ?""",
                (session_id, limit),
            ).fetchall()
        out = []
        for r in reversed(rows):
            out.append(
                {
                    "role": r["role"],
                    "content": r["content"],
                    "tool_call_id": r["tool_call_id"],
                    "name": r["name"],
                    "tool_calls": json.loads(r["tool_calls_json"])
                    if r["tool_calls_json"]
                    else None,
                    "created_at": r["created_at"],
                }
            )
        return out

    def conversation_clear(self, session_id: str) -> None:
        with self._tx() as conn:
            conn.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))

    def approval_save(self, data: dict[str, Any]) -> None:
        with self._tx() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO approvals
                   (id, action, tool_name, details_json, risk_level, action_hash,
                    user_id, session_id, status, message_to_user, edited_payload_json,
                    consumed, created_at, expires_at, resolved_at, resolved_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["id"],
                    data["action"],
                    data["tool_name"],
                    json.dumps(data.get("details") or {}),
                    data["risk_level"],
                    data["action_hash"],
                    data.get("user_id", "default"),
                    data.get("session_id", "default"),
                    data["status"],
                    data.get("message_to_user", ""),
                    json.dumps(data["edited_payload"])
                    if data.get("edited_payload") is not None
                    else None,
                    1 if data.get("consumed") else 0,
                    _dt(data.get("created_at") or datetime.utcnow()),
                    _dt(data["expires_at"]),
                    _dt(data.get("resolved_at")),
                    data.get("resolved_by"),
                ),
            )

    def approval_get(self, approval_id: str) -> dict[str, Any] | None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE id=?", (approval_id,)
            ).fetchone()
        return self._approval_row(row) if row else None

    def approval_list_pending(self) -> list[dict[str, Any]]:
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE status='pending' ORDER BY created_at"
            ).fetchall()
        return [self._approval_row(r) for r in rows]

    @staticmethod
    def _approval_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "action": row["action"],
            "tool_name": row["tool_name"],
            "details": json.loads(row["details_json"] or "{}"),
            "risk_level": row["risk_level"],
            "action_hash": row["action_hash"],
            "user_id": row["user_id"],
            "session_id": row["session_id"],
            "status": row["status"],
            "message_to_user": row["message_to_user"],
            "edited_payload": json.loads(row["edited_payload_json"])
            if row["edited_payload_json"]
            else None,
            "consumed": bool(row["consumed"]),
            "created_at": _parse_dt(row["created_at"]),
            "expires_at": _parse_dt(row["expires_at"]),
            "resolved_at": _parse_dt(row["resolved_at"]),
            "resolved_by": row["resolved_by"],
        }

    def task_save(self, data: dict[str, Any]) -> None:
        with self._tx() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO scheduled_tasks
                   (id, user_id, name, prompt, kind, run_at, time_of_day, cron,
                    interval_seconds, timezone, status, last_run_at, next_run_at,
                    metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["id"],
                    data.get("user_id", "default"),
                    data["name"],
                    data["prompt"],
                    data["kind"],
                    _dt(data.get("run_at")),
                    data.get("time_of_day"),
                    data.get("cron"),
                    data.get("interval_seconds"),
                    data.get("timezone", "Asia/Tehran"),
                    data["status"],
                    _dt(data.get("last_run_at")),
                    _dt(data.get("next_run_at")),
                    json.dumps(data.get("metadata") or {}),
                    _dt(data.get("created_at") or datetime.utcnow()),
                ),
            )

    def task_list(self, user_id: str | None = None) -> list[dict[str, Any]]:
        with self._tx() as conn:
            if user_id:
                rows = conn.execute(
                    "SELECT * FROM scheduled_tasks WHERE user_id=? ORDER BY created_at",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM scheduled_tasks ORDER BY created_at"
                ).fetchall()
        return [self._task_row(r) for r in rows]

    def task_get(self, task_id: str) -> dict[str, Any] | None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE id=?", (task_id,)
            ).fetchone()
        return self._task_row(row) if row else None

    @staticmethod
    def _task_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "prompt": row["prompt"],
            "kind": row["kind"],
            "run_at": _parse_dt(row["run_at"]),
            "time_of_day": row["time_of_day"],
            "cron": row["cron"],
            "interval_seconds": row["interval_seconds"],
            "timezone": row["timezone"],
            "status": row["status"],
            "last_run_at": _parse_dt(row["last_run_at"]),
            "next_run_at": _parse_dt(row["next_run_at"]),
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "created_at": _parse_dt(row["created_at"]),
        }

    def setting_get(self, key: str) -> str | None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key=?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def setting_set(self, key: str, value: str) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings(key, value) VALUES (?, ?)",
                (key, value),
            )


from app.database.run_store_mixin import attach_run_methods

attach_run_methods(SQLiteStore)

_store: SQLiteStore | None = None
_store_lock = threading.Lock()


def get_store(db_path: Path | None = None) -> SQLiteStore:
    global _store
    with _store_lock:
        if _store is None or (db_path is not None and _store.db_path != db_path):
            _store = SQLiteStore(db_path=db_path)
        return _store


def reset_store_for_tests(db_path: Path) -> SQLiteStore:
    """Force a fresh store pointing at a temp DB (tests only)."""
    global _store
    with _store_lock:
        if db_path.exists():
            db_path.unlink()
        for suffix in ("-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        _store = SQLiteStore(db_path=db_path)
        return _store
