from __future__ import annotations
import asyncio, uuid, re, json
from typing import Any, Dict, Optional
from .base_agent import BaseAgent

SMALLTALK_MAX_LEN = 200

def _extract_display_note(payload: Dict[str, Any]) -> Optional[str]:
    note = (payload or {}).get("note")
    if note:
        return note
    res = (payload or {}).get("result")
    if isinstance(res, dict) and res.get("ok"):
        try:
            return json.dumps(res, ensure_ascii=True)
        except Exception:
            return str(res)
    return None

class CommsAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("ui/print", {"text": f"{self.name}: Comms online."}, sender=self.name)
        status_task = asyncio.create_task(self._status_consumer())

        async for env in self.bus.subscribe("user/text"):
            text = (env.payload or {}).get("text", "").strip()
            if not text:
                continue

            if self._is_smalltalk(text):
                reply = await self._smalltalk_reply(text)
                await self.bus.publish("ui/print", {"text": f"{self.name}: {reply}"}, sender=self.name)
                continue

            job = uuid.uuid4().hex[:8]
            await self.bus.publish("ui/print", {"text": f"{self.name}: Got it. Handing to Brain (job {job})."}, sender=self.name, job_id=job)
            await self.bus.publish("task/new", {"text": text}, sender=self.name, job_id=job)
            # Bridge to aligned schema
            await self.bus.publish("user/request", {"text": text}, sender=self.name, job_id=job)

        status_task.cancel()
        try:
            await status_task
        except asyncio.CancelledError:
            pass

    async def _status_consumer(self):
        async def plans():
            async for env in self.bus.subscribe("task/plan"):
                plan = env.payload.get("plan") or env.payload
                title = (plan.get("title") if isinstance(plan, dict) else None) or "Plan"
                steps = plan.get("steps", []) if isinstance(plan, dict) else []
                nsteps = len(steps) if isinstance(steps, list) else 0
                await self.bus.publish("ui/print", {"text": f"{self.name}: Plan ready: {title} - {nsteps} step(s)."}, sender=self.name, job_id=env.job_id)

        async def worker():
            async for env in self.bus.subscribe("worker/done"):
                summary = _extract_display_note(env.payload) or "Worker completed."
                await self.bus.publish("ui/print", {"text": f"{self.name}: [OK] Done: {summary}"}, sender=self.name, job_id=env.job_id)

        async def tests():
            async for env in self.bus.subscribe_prefix("test/"):
                if env.topic.endswith("passed"):
                    await self.bus.publish("ui/print", {"text": f"{self.name}: [OK] Tests PASS."}, sender=self.name, job_id=env.job_id)
                elif env.topic.endswith("failed"):
                    reason = (env.payload or {}).get("reason") or "Unknown"
                    await self.bus.publish("ui/print", {"text": f"{self.name}: [FAIL] Tests FAIL - {reason}"}, sender=self.name, job_id=env.job_id)

        await asyncio.gather(plans(), worker(), tests())

    # --- small talk ---

    def _is_smalltalk(self, text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return False
        if re.match(r"^\s*(hi|hey|hello|yo|sup|what'?s up|wazz?up)\b", t, flags=re.IGNORECASE):
            return True
        if re.search(r"\b(how are you|how's it going|how is it going|what'?s up|wazz? ?up)\b", t, flags=re.IGNORECASE):
            return True
        if len(t) <= SMALLTALK_MAX_LEN and re.fullmatch(r"(thx|thanks|thank you|ok|cool|nice|great|awesome)[!.?]*", t, flags=re.IGNORECASE):
            return True
        return False

    async def _smalltalk_reply(self, text: str) -> str:
        if re.search(r"\bhow are you\b", text, flags=re.IGNORECASE):
            return "Doing well and ready - what should I do?"
        if re.match(r"^\s*(hi|hey|hello)\b", text, flags=re.IGNORECASE):
            return "Hello! What would you like me to do?"
        return "Got you. What would you like me to do?"
