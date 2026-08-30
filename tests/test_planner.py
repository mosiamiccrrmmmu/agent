import pytest

from app.agent.planner import DeterministicPlanner


@pytest.mark.asyncio
async def test_plan_search():
    p = await DeterministicPlanner().create_plan("search the web for news")
    assert p.steps
    assert any(s.tool == "search_web" for s in p.steps)


@pytest.mark.asyncio
async def test_plan_launch():
    p = await DeterministicPlanner().create_plan("open notepad")
    assert any(s.tool == "launch_app" for s in p.steps)


@pytest.mark.asyncio
async def test_plan_default_chat():
    p = await DeterministicPlanner().create_plan("hello how are you")
    assert len(p.steps) >= 1
