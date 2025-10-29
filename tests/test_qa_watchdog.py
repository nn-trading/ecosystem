# C:\bots\ecosys\tests\test_qa_watchdog.py
import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..")))

import os
import asyncio
import contextlib

from core.bus import EventBus
from agents.tester_agent import TesterAgent


async def _watch_all(bus: EventBus, out: list):
    async for env in bus.subscribe_prefix(""):
        out.append((env.topic, env.payload, env.job_id))


def _copy_plan():
    return {
        "steps": [
            {"type": "tool", "tool": "ui.hotkey", "args": {"keys": ["ctrl", "c"]}}
        ]
    }


def test_qa_watchdog_counts_and_summary_pass_only():
    asyncio.run(_test_qa_watchdog_counts_and_summary_pass_only())


async def _test_qa_watchdog_counts_and_summary_pass_only():
    os.environ["QA_WATCHDOG_N"] = "3"
    bus = EventBus()
    tester = TesterAgent("Tester", bus, llm=None, memory=None, tools=None)

    events = []
    wtask = asyncio.create_task(_watch_all(bus, events))
    ttask = asyncio.create_task(tester.run())
    await asyncio.sleep(0.05)

    job_id = "Q1"
    for i in range(3):
        await bus.publish("task/plan", _copy_plan(), sender="test", job_id=job_id)
        await asyncio.sleep(0.01)
        await bus.publish("task/result", {"text": f"ok-{i}"}, sender="worker", job_id=job_id)
        await asyncio.sleep(0.02)

    # allow final summary to emit
    await asyncio.sleep(0.1)

    for t in (wtask, ttask):
        t.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t

    ui_msgs = [e[1].get("text", "") for e in events if e[0] == "ui/print" and e[2] == job_id]
    assert any("QA PASS #1" in m for m in ui_msgs)
    assert any("QA PASS #2" in m for m in ui_msgs)
    assert any("QA PASS #3" in m for m in ui_msgs)
    assert any("QA watchdog complete: 3 pass, 0 fail" in m for m in ui_msgs)


def test_qa_watchdog_counts_and_summary_with_fail():
    asyncio.run(_test_qa_watchdog_counts_and_summary_with_fail())


async def _test_qa_watchdog_counts_and_summary_with_fail():
    os.environ["QA_WATCHDOG_N"] = "3"
    bus = EventBus()
    tester = TesterAgent("Tester", bus, llm=None, memory=None, tools=None)

    events = []
    wtask = asyncio.create_task(_watch_all(bus, events))
    ttask = asyncio.create_task(tester.run())
    await asyncio.sleep(0.05)

    job_id = "Q2"
    # PASS
    await bus.publish("task/plan", _copy_plan(), sender="test", job_id=job_id)
    await asyncio.sleep(0.01)
    await bus.publish("task/result", {"text": "ok"}, sender="worker", job_id=job_id)
    await asyncio.sleep(0.02)
    # FAIL (empty clipboard)
    await bus.publish("task/plan", _copy_plan(), sender="test", job_id=job_id)
    await asyncio.sleep(0.01)
    await bus.publish("task/result", {"text": ""}, sender="worker", job_id=job_id)
    await asyncio.sleep(0.02)
    # PASS
    await bus.publish("task/plan", _copy_plan(), sender="test", job_id=job_id)
    await asyncio.sleep(0.01)
    await bus.publish("task/result", {"text": "ok again"}, sender="worker", job_id=job_id)

    await asyncio.sleep(0.15)

    for t in (wtask, ttask):
        t.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t

    ui_msgs = [e[1].get("text", "") for e in events if e[0] == "ui/print" and e[2] == job_id]
    assert any("QA PASS #1" in m for m in ui_msgs)
    assert any("QA FAIL #2: empty clipboard" in m for m in ui_msgs)
    assert any("QA PASS #2" in m for m in ui_msgs) or any("QA PASS #3" in m for m in ui_msgs)
    assert any("QA watchdog complete: 2 pass, 1 fail" in m for m in ui_msgs)
