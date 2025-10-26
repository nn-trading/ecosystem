# ASCII-only smoke tests for TesterAgent
import asyncio

# Minimal Bus stub compatible with our bus.EventBus adapters
class StubBus:
    def __init__(self):
        self.handlers = {}
        self.published = []
    def on(self, topic, handler):
        self.handlers.setdefault(topic, []).append(handler)
    async def publish(self, topic, payload, *, sender, job_id=None):
        self.published.append((topic, payload, sender, job_id))
        # Immediately deliver to handlers
        for h in self.handlers.get(topic, []):
            msg = {"topic": topic, "data": payload, "job_id": job_id}
            if asyncio.iscoroutinefunction(h):
                await h(msg)
            else:
                r = h(msg)
                if asyncio.iscoroutine(r):
                    await r

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

def test_copy_pass_emits_test_passed():
    from agents.tester_agent import TesterAgent
    async def _test():
        bus = StubBus()
        ag = TesterAgent("AI-4:Tester", bus, None, None, None)
        task = asyncio.create_task(ag.run())
        await asyncio.sleep(0)
        plan = {"steps": [
            {"type":"tool","tool":"ui.hotkey","args":{"keys":["ctrl","c"]}}
        ]}
        await bus.publish("task/plan", plan, sender="test")
        await bus.publish("task/result", {"text":"hello"}, sender="test")
        assert any(t=="test/passed" and p.get("length")==5 for (t,p,_,_) in bus.published)
        task.cancel()
        try:
            await task
        except Exception:
            pass
    _run(_test())

def test_copy_fail_emits_test_failed_and_corrective_task():
    from agents.tester_agent import TesterAgent
    async def _test():
        bus = StubBus()
        ag = TesterAgent("AI-4:Tester", bus, None, None, None)
        task = asyncio.create_task(ag.run())
        await asyncio.sleep(0)
        plan = {"steps": [
            {"type":"tool","tool":"ui.hotkey","args":{"keys":["ctrl","c"]}}
        ]}
        await bus.publish("task/plan", plan, sender="test")
        await bus.publish("task/result", {"text":""}, sender="test")
        topics = [t for (t,_,_,_) in bus.published]
        assert "test/failed" in topics
        assert "task/new" in topics
        task.cancel()
        try:
            await task
        except Exception:
            pass
    _run(_test())
