# Tests for EventBus adapters and prefix subscription
import asyncio
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.bus import EventBus


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for t in pending:
                t.cancel()
            loop.run_until_complete(asyncio.sleep(0))
        except Exception:
            pass
        loop.close()


def test_bus_on_adapter_dict_shape():
    async def _test():
        bus = EventBus()
        got = []
        fut = asyncio.Future()
        def handler(msg):
            got.append(msg)
            if not fut.done():
                fut.set_result(True)
        bus.on("alpha", handler)
        # Give the on() runner a chance to subscribe before publishing
        await asyncio.sleep(0)
        await bus.publish("alpha", {"x": 1}, sender="test")
        await asyncio.wait_for(fut, timeout=1.0)
        assert len(got) == 1
        m = got[0]
        assert isinstance(m, dict)
        assert m.get("topic") == "alpha"
        assert m.get("data") == {"x": 1}
        assert "job_id" in m
    _run(_test())


def test_subscribe_prefix_collects_multiple_topics():
    async def _test():
        bus = EventBus()
        received = []
        done = asyncio.Event()
        async def collector():
            async for env in bus.subscribe_prefix("task/"):
                received.append(env.topic)
                if len(received) >= 2:
                    done.set()
                    break
        task = asyncio.create_task(collector())
        await asyncio.sleep(0)
        await bus.publish("task/exec", {"a": 1}, sender="tester")
        await bus.publish("task/result", {"b": 2}, sender="tester")
        await asyncio.wait_for(done.wait(), timeout=1.0)
        task.cancel()
        try:
            await task
        except Exception:
            pass
        assert "task/exec" in received and "task/result" in received
    _run(_test())
