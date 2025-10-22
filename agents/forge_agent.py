import asyncio
import json
from pathlib import Path
from agents.base_agent import BaseAgent

SKELETONS = {
    "agents/architect_agent.py": """import asyncio
from agents.base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("comms/out", {"text": "[Architect] online"}, sender=self.name)
        while True:
            await asyncio.sleep(3600)
""",
    "agents/planner_agent.py": """import asyncio
from agents.base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("comms/out", {"text": "[Planner] online"}, sender=self.name)
        while True:
            await asyncio.sleep(3600)
""",
    "agents/executor_agent.py": """import asyncio
from agents.base_agent import BaseAgent

class ExecutorAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("comms/out", {"text": "[Executor] online"}, sender=self.name)
        while True:
            await asyncio.sleep(3600)
""",
    "agents/auditor_agent.py": """import asyncio
from agents.base_agent import BaseAgent

class AuditorAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("comms/out", {"text": "[Auditor] online"}, sender=self.name)
        while True:
            await asyncio.sleep(3600)
""",
}

class ForgeAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("comms/out", {"text": "[Forge] online"}, sender=self.name)
        root = Path(__file__).resolve().parent.parent
        async for env in self.bus.subscribe("comms/in"):
            try:
                line = (env.payload.get("text") or "").strip().lower()
                if line.startswith("/forge agents"):
                    created = []
                    for rel, code in SKELETONS.items():
                        p = (root / rel).resolve()
                        p.parent.mkdir(parents=True, exist_ok=True)
                        if not p.exists():
                            p.write_text(code, encoding="utf-8")
                            created.append(p.name)
                    msg = {"created": created, "dir": str((root / "agents").resolve())}
                    await self.bus.publish("comms/out", {"text": json.dumps(msg, indent=4)}, sender=self.name)
            except Exception as e:
                await self.bus.publish("comms/out", {"text": f"Forge error: {e!r}"}, sender=self.name)
