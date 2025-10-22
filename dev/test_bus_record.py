import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
from core.bus import EventBus
from core.memory import Memory
from main import bus_recorder

async def run():
    bus = EventBus()
    memory = Memory()
    before = memory.count_lines()
    rec = asyncio.create_task(bus_recorder(bus, memory))
    await asyncio.sleep(0)
    await bus.publish("test/event1", {"x": 1}, sender="tester")
    await bus.publish("test/event2", {"x": 2}, sender="tester")
    await asyncio.sleep(0.3)
    rec.cancel()
    try:
        await rec
    except BaseException:
        pass
    after = memory.count_lines()
    print(f"before={before} after={after}")
    print(memory.events_path)
    tail = memory.tail_events(3)
    for obj in tail:
        print(obj.get("topic"), obj.get("sender"))

if __name__ == "__main__":
    asyncio.run(run())
