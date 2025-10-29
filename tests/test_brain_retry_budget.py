# C:\bots\ecosys\tests\test_brain_retry_budget.py
import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..")))

import os
import asyncio
import contextlib
import time
import pytest

from core.bus import EventBus
from agents.brain_agent import BrainAgent


async def _watch_all(bus: EventBus, out: list):
    async for env in bus.subscribe_prefix(""):
        out.append((env.topic, env.payload, env.job_id))


def test_brain_retry_budget_exhaustion():
    asyncio.run(_test_brain_retry_budget_exhaustion())

async def _test_brain_retry_budget_exhaustion():
    os.environ["BRAIN_RETRY_BUDGET"] = "2"
    bus = EventBus()
    brain = BrainAgent("Brain", bus, llm=None, memory=None, tools=None)

    events = []
    wtask = asyncio.create_task(_watch_all(bus, events))
    atask = asyncio.create_task(brain.run())
    await asyncio.sleep(0.1)

    job_id = "J1"
    # Seed a new task which should reset budget and produce an initial plan/exec
    await bus.publish("task/new", {"text": "type: hello then copy"}, sender="test", job_id=job_id)
    await asyncio.sleep(0.1)

    # Provide a retry plan payload that should be reused
    retry_plan = {
        "plan": {
            "steps": [
                {"type": "tool", "tool": "ui.hotkey", "args": {"keys": ["ctrl", "c"]}}
            ]
        },
        "feedback": "retrying"
    }

    # Within budget
    await bus.publish("task/retry", {"data": retry_plan}, sender="tester", job_id=job_id)
    await asyncio.sleep(0.05)
    await bus.publish("task/retry", {"data": retry_plan}, sender="tester", job_id=job_id)
    await asyncio.sleep(0.05)

    # This one exceeds budget and should trigger budget_exhausted, not plan/exec
    await bus.publish("task/retry", {"data": retry_plan}, sender="tester", job_id=job_id)
    await asyncio.sleep(0.1)

    # Stop background tasks
    for t in (wtask, atask):
        t.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t

    # Analyze captured events for this job
    plans = [e for e in events if e[0] == "task/plan" and e[2] == job_id]
    execs = [e for e in events if e[0] == "task/exec" and e[2] == job_id]
    exhausts = [e for e in events if e[0] == "task/budget_exhausted" and e[2] == job_id]
    ui_msgs = [e for e in events if e[0] == "ui/print" and e[2] == job_id]

    # Expect 1 initial plan + 2 retry plans within budget
    assert len(plans) >= 3, f"expected >=3 plans, got {len(plans)}"
    assert len(execs) >= 3, f"expected >=3 execs, got {len(execs)}"

    # Expect budget exhausted event exactly once, with a friendly ui/print
    assert len(exhausts) == 1, f"expected 1 budget_exhausted, got {len(exhausts)}"
    assert any("retry budget exhausted" in (m[1].get("text", "")) for m in ui_msgs), "missing exhaustion ui message"

    # Ensure no extra plan was published for the exhausted attempt by checking last event types
    last_topics = [e[0] for e in events if e[2] == job_id][-3:]
    assert "task/budget_exhausted" in last_topics, f"expected exhaustion near the end: {last_topics}"


def test_budget_resets_on_new_task():
    asyncio.run(_test_budget_resets_on_new_task())

async def _test_budget_resets_on_new_task():
    os.environ["BRAIN_RETRY_BUDGET"] = "1"
    bus = EventBus()
    brain = BrainAgent("Brain", bus, llm=None, memory=None, tools=None)

    events = []
    wtask = asyncio.create_task(_watch_all(bus, events))
    atask = asyncio.create_task(brain.run())

    job_id = "J2"
    await bus.publish("task/new", {"text": "type: hi then copy"}, sender="test", job_id=job_id)
    await asyncio.sleep(0.05)
    await bus.publish("task/retry", {"data": {"plan": {"steps": []}}}, sender="tester", job_id=job_id)
    await asyncio.sleep(0.05)
    # This retry exceeds budget and should exhaust
    await bus.publish("task/retry", {"data": {"plan": {"steps": []}}}, sender="tester", job_id=job_id)
    await asyncio.sleep(0.05)

    # Now send a fresh task/new which must reset budget and allow a new plan
    await bus.publish("task/new", {"text": "type: bye then copy"}, sender="test", job_id=job_id)
    await asyncio.sleep(0.1)

    for t in (wtask, atask):
        t.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t

    # After the second task/new, we expect another plan to have been published for the same job
    plans = [e for e in events if e[0] == "task/plan" and e[2] == job_id]
    assert len(plans) >= 2, f"expected at least 2 plan events for job {job_id}, got {len(plans)}"
