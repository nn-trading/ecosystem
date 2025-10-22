# C:\bots\ecosys\agents\logger_agent.py
from __future__ import annotations

import os
from agents.base_agent import BaseAgent
from memory.eventlog import EventLog

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip())
    except Exception:
        return default

LOGGER_MAX_KEEP = _int_env("LOGGER_MAX_KEEP", 500_000)
LOGGER_RECENT_FOR_COMMS = _int_env("LOGGER_RECENT_FOR_COMMS", 200)

class LoggerAgent(BaseAgent):
    def __init__(self, name: str, bus, llm=None, memory=None, tools=None, *args, **kwargs):
        """
        Keep signature compatible with main.py which passes (name, bus, llm, memory, tools).
        Any extra args are ignored to avoid future mismatches.
        """
        # If BaseAgent supports (name, bus, llm, memory, tools), pass them through.
        try:
            super().__init__(name, bus, llm, memory, tools)  # type: ignore[arg-type]
        except TypeError:
            # Fallback for older BaseAgent that only takes (name, bus, llm)
            super().__init__(name, bus, llm)  # type: ignore[arg-type]

        self.log = EventLog()

    async def _say(self, text: str):
        await self.bus.publish("ui/print", {"text": f"{self.name}: {text}"}, sender=self.name)

    async def run(self):
        await self._say("Logger initialized. Building summary…")

        # Roll up old events to keep DB lean
        rolled = self.log.rollup(max_keep=LOGGER_MAX_KEEP)
        stats = self.log.stats()

        # Human-readable banner like before
        top_topics_str = ", ".join(f"{k}×{v}" for (k, v) in rolled.get("top_topics", [])) or "—"
        summary_text = (
            "## Session Summary (rolling)\n\n"
            f"- Lines summarized: {rolled.get('summarized', 0)}\n"
            f"- Kept recent: {rolled.get('kept', 0)} (max {LOGGER_MAX_KEEP})\n"
            f"- Top (rolled) topics: {top_topics_str}\n"
        )
        await self.bus.publish("memory/summary", {"text": summary_text}, sender=self.name)

        # Compact recent context for Comms/others (if they listen)
        recent = self.log.recent(LOGGER_RECENT_FOR_COMMS)
        await self.bus.publish("memory/context", {
            "recent": recent,
            "count": len(recent),
            "max_keep": LOGGER_MAX_KEEP,
            "stats": stats
        }, sender=self.name)

        await self._say("Summary ready.")

        # Subscribe to EVERYTHING and append
        async for env in self.bus.subscribe_prefix(""):
            try:
                self.log.append(env.topic, env.sender, env.payload)
            except Exception as e:
                # Never crash logger; surface a minimal warning
                await self.bus.publish("ui/print", {
                    "text": f"{self.name}: WARN could not log event {env.topic}: {e}"
                }, sender=self.name)
