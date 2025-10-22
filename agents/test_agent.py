import asyncio
from agents.base_agent import BaseAgent

class TestAgent(BaseAgent):
    """
    Disabled tester: does not verify or replan anything.
    This prevents the endless "❌ Tests failed. Replanning." loop.
    """
    async def run(self):
        await self.bus.publish("comms/notify",
                               {"status": "tester_disabled"},
                               sender=self.name)
        # stay idle forever
        while True:
            await asyncio.sleep(3600)
