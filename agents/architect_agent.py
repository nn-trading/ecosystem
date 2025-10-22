import asyncio
from agents.base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("comms/out", {"text": "[Architect] online"}, sender=self.name)
        while True:
            await asyncio.sleep(3600)
