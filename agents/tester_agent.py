# C:\bots\ecosys\agents\tester_agent.py
from __future__ import annotations
import asyncio
import inspect
import re
from typing import Any, Optional

COPY_RX = re.compile(r'\bcopy\b', re.IGNORECASE)

class TesterAgent:
    def __init__(self, name: str, bus: Any, llm: Any, memory: Any, tools: Any):
        self.name = name
        self.bus = bus
        self.llm = llm
        self.memory = memory
        self.tools = tools
        self._awaiting_copy: bool = False  # set True when a plan asked for copy

    def _saw_copy(self, plan: dict) -> bool:
        try:
            for st in plan.get("steps", []):
                if st.get("type") == "tool" and st.get("tool") == "ui.hotkey":
                    if st.get("args", {}).get("keys") == ["ctrl", "c"]:
                        return True
        except Exception:
            pass
        return False

    async def run(self) -> None:
        try:
            on = getattr(self.bus, "on", None)
            if callable(on):
                async def _plan_handler(msg: Any) -> None:
                    if isinstance(msg, dict) and msg.get("topic") == "task/plan":
                        data = msg.get("data", {})
                        self._awaiting_copy = self._saw_copy(data)

                async def _result_handler(msg: Any) -> None:
                    if isinstance(msg, dict) and msg.get("topic") == "task/result":
                        if not self._awaiting_copy:
                            return
                        self._awaiting_copy = False
                        txt = str(msg.get("data", {}).get("text", "")).strip()
                        if not txt:
                            # re-issue a corrective task
                            fix = "focus notepad then press ctrl+a, ctrl+c (copy again)"
                            pub = getattr(self.bus, "emit", None) or getattr(self.bus, "publish", None) or getattr(self.bus, "send", None)
                            if callable(pub):
                                r = pub("task/new", {"text": fix}, sender=self.name)  # type: ignore
                                if inspect.isawaitable(r):
                                    await r

                # subscribe
                r1 = on("task/plan", _plan_handler)
                r2 = on("task/result", _result_handler)
                if inspect.isawaitable(r1): await r1
                if inspect.isawaitable(r2): await r2
                while True:
                    await asyncio.sleep(3600)

            # fallback idle
            while True:
                await asyncio.sleep(3600)

        except Exception as e:
            print(f"{self.name}: run() warning: {e.__class__.__name__}: {e}")
            while True:
                await asyncio.sleep(3600)
