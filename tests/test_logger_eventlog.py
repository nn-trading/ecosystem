# Tests for LoggerAgent and EventLog behavior (ASCII-safe)
import asyncio, os, sqlite3, tempfile, uuid, json
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class Env:
    def __init__(self, topic, payload=None, sender=None, job_id=None):
        self.topic = topic
        self.payload = payload or {}
        self.sender = sender
        self.job_id = job_id

class StubBus:
    def __init__(self):
        self._q = asyncio.Queue()
        self.published = []  # list of (topic, payload, sender, job_id)
    async def publish(self, topic, payload, *, sender, job_id=None):
        self.published.append((topic, payload, sender, job_id))
        await self._q.put(Env(topic, payload, sender, job_id))
    async def subscribe_prefix(self, prefix: str):
        while True:
            env = await self._q.get()
            yield env


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


def test_logger_skips_memory_context_and_compacts():
    # Unique temp DB
    db = os.path.join(tempfile.gettempdir(), f"ecosys_test_{uuid.uuid4().hex}.db")
    os.environ['ECOSYS_MEMORY_DB'] = db
    # Keep payload limit generous for this test
    os.environ.pop('EVENTLOG_MAX_PAYLOAD', None)

    async def _test():
        from agents.logger_agent import LoggerAgent
        bus = StubBus()
        ag = LoggerAgent("AI-5:Logger", bus, None, None, None)
        task = asyncio.create_task(ag.run())
        await asyncio.sleep(0.05)
        # Send a normal event and a memory/context event
        await bus.publish("foo/bar", {"x": 1}, sender="test")
        await bus.publish("memory/context", {"ignored": True}, sender="test")
        # Trigger resummarize to force another compact context publish
        await bus.publish("log/resummarize", {}, sender="test")
        await asyncio.sleep(0.1)
        # Stop logger
        task.cancel()
        try:
            await task
        except Exception:
            pass
        # DB checks
        con = sqlite3.connect(db)
        cur = con.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM events WHERE topic=?", ("memory/context",))
            c = cur.fetchone()[0]
        finally:
            con.close()
        assert c == 0, "LoggerAgent must skip persisting memory/context events"
        # Check that a compact memory/context was published with payload_keys
        got_ctx = [p for (t,p,_,_) in bus.published if t=="memory/context"]
        assert got_ctx, "LoggerAgent should publish compact memory/context"
        rc = got_ctx[-1]
        assert isinstance(rc.get("recent"), list)
        if rc["recent"]:
            assert "payload_keys" in rc["recent"][0]

    _run(_test())


def test_eventlog_truncates_oversize_payload():
    db = os.path.join(tempfile.gettempdir(), f"ecosys_test_{uuid.uuid4().hex}.db")
    os.environ['ECOSYS_MEMORY_DB'] = db
    os.environ['EVENTLOG_MAX_PAYLOAD'] = '1024'  # 1 KB threshold to force truncation

    async def _test():
        from agents.logger_agent import LoggerAgent
        bus = StubBus()
        ag = LoggerAgent("AI-5:Logger", bus, None, None, None)
        task = asyncio.create_task(ag.run())
        await asyncio.sleep(0.05)
        big_payload = {"data": "x" * 5000}
        await bus.publish("big/payload", big_payload, sender="test")
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except Exception:
            pass
        con = sqlite3.connect(db)
        try:
            cur = con.cursor()
            cur.execute("SELECT payload_json FROM events WHERE topic=? ORDER BY id DESC LIMIT 1", ("big/payload",))
            row = cur.fetchone()
        finally:
            con.close()
        assert row is not None
        try:
            pj = json.loads(row[0])
        except Exception:
            pj = {"_raw": row[0]}
        assert pj.get("_truncated") is True or (isinstance(row[0], str) and '"_truncated"' in row[0]), "Oversize payloads should be truncated with marker"

