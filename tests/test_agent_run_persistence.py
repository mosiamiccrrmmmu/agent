from pathlib import Path

from app.database.sqlite_store import SQLiteStore


def test_upsert_and_get_run(tmp_path: Path):
    store = SQLiteStore(db_path=tmp_path / "runs.db")
    store.upsert_agent_run(
        "run-1",
        session_id="s1",
        status="running",
        goal="test goal",
        plan={"steps": []},
        started=True,
    )
    row = store.get_agent_run("run-1")
    assert row is not None
    assert row["status"] == "running"
    assert row["goal"] == "test goal"

    store.upsert_agent_run(
        "run-1",
        status="completed",
        goal="test goal",
        finished=True,
        current_step=3,
    )
    row2 = store.get_agent_run("run-1")
    assert row2["status"] == "completed"
    assert row2["finished_at"] is not None


def test_mark_stale(tmp_path: Path):
    store = SQLiteStore(db_path=tmp_path / "stale.db")
    store.upsert_agent_run("r2", status="running", goal="x", started=True)
    n = store.mark_stale_running_runs()
    assert n >= 1
    assert store.get_agent_run("r2")["status"] == "failed"
