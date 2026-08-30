import pytest

from app.agent.cancel import clear_agent_cancel, request_agent_cancel
from app.agent.execution.engine import ExecutionEngine, ExecutionStep


@pytest.mark.asyncio
async def test_execute_two_steps():
    clear_agent_cancel()
    calls: list[str] = []

    async def executor(tool: str, args: dict):
        calls.append(tool)
        return {"success": True, "data": args}

    engine = ExecutionEngine(max_retries=0)
    steps = [
        ExecutionStep(tool="a", arguments={"x": 1}),
        ExecutionStep(tool="b", arguments={"y": 2}),
    ]
    result = await engine.execute(steps, executor, run_id="r1")
    assert result.status == "completed"
    assert calls == ["a", "b"]


@pytest.mark.asyncio
async def test_mid_loop_cancel_skips_second_step():
    clear_agent_cancel()
    calls: list[str] = []

    async def executor(tool: str, args: dict):
        calls.append(tool)
        if tool == "step1":
            request_agent_cancel()
        return {"success": True, "data": True}

    engine = ExecutionEngine(max_retries=0)
    steps = [
        ExecutionStep(tool="step1", arguments={}),
        ExecutionStep(tool="step2", arguments={}),
    ]
    result = await engine.execute(steps, executor, run_id="r-cancel")
    assert result.status == "cancelled"
    assert calls == ["step1"]
    assert any(s.tool == "step2" and s.status.value == "skipped" for s in result.steps)


@pytest.mark.asyncio
async def test_cancel_persisted_in_sqlite(tmp_path):
    clear_agent_cancel()
    from app.database.sqlite_store import SQLiteStore

    store = SQLiteStore(db_path=tmp_path / "exec.db")

    async def executor(tool: str, args: dict):
        request_agent_cancel()
        return {"success": True}

    engine = ExecutionEngine()
    steps = [
        ExecutionStep(tool="x", arguments={}),
        ExecutionStep(tool="y", arguments={}),
    ]
    result = await engine.execute(steps, executor, run_id="persist-cancel")
    store.upsert_agent_run(
        result.run_id,
        status=result.status,
        goal="test",
        finished=True,
        error=result.error,
        started=True,
    )
    row = store.get_agent_run(result.run_id)
    assert row is not None
    assert row["status"] == "cancelled"
