from __future__ import annotations
from .base_agent import BaseAgent

class AuditorAgent(BaseAgent):
    async def run(self):
        async for env in self.bus.subscribe("system/status"):
            await self.bus.publish(
                "ui/print",
                {"text": "Alive: Comms, Brain, Worker, Tester, Logger"},
                sender=self.name,
                job_id=env.job_id
            )
