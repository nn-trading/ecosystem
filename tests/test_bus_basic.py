import asyncio
import pytest
from core.bus import EventBus

@pytest.mark.asyncio
async def test_publish_subscribe_roundtrip():
    bus = EventBus()
    got = []
    async def consumer():
        async for env in bus.subscribe("x/y"):
            got.append(env.payload.get("v"))
            break
    t = asyncio.create_task(consumer())
    await asyncio.sleep(0)  # let subscription register
    await bus.publish("x/y", {"v": 42}, sender="test")
    await asyncio.wait_for(t, timeout=2)
    assert got == [42]
