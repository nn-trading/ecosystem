from __future__ import annotations
from typing import Optional

class BaseAgent:
    def __init__(self, name, bus, llm, memory, tools):
        self.name = name
        self.bus = bus
        self.llm = llm
        self.memory = memory
        self.tools = tools

    async def say(self, text: str, *, job_id: Optional[str] = None):
        try:
            self.memory.append("assistant", f"{self.name}: {text}")
        except Exception:
            pass
        await self.bus.publish("ui/print", {"text": f"{self.name}: {text}"}, sender=self.name, job_id=job_id)
