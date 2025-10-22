import asyncio, inspect, json, os
from agents.base_agent import BaseAgent

ALLOW_DANGEROUS = os.environ.get("AI_ALLOW_DANGEROUS", "0") == "1"
BLOCK_SHELL = [] if ALLOW_DANGEROUS else ["format", "diskpart", "reg", "bcdedit", "cipher", "shutdown"]

class ExecutorAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("comms/out", {"text": "[Executor] online"}, sender=self.name)

        async for env in self.bus.subscribe("exec/request"):
            payload = env.payload or {}
            steps = payload.get("steps") or []
            origin = payload.get("origin") or ""

            results = []
            for idx, step in enumerate(steps):
                result = await self._run_step(idx, step)
                results.append(result)

            done = {"origin": origin, "results": results}
            await self.bus.publish("exec/done", done, sender=self.name)

    async def _run_step(self, idx, step):
        tool = step.get("tool")
        args = dict(step.get("args") or {})

        ok = True
        res = None
        err = None

        try:
            if tool == "shell.run" and not ALLOW_DANGEROUS:
                # quick guardrail
                cmd = (args.get("cmd") or "").lower().strip()
                if any(bad in cmd for bad in BLOCK_SHELL):
                    raise RuntimeError(f"blocked shell command: {cmd!r}")

            call = self.tools.call(tool, **args)
            res = await call if inspect.iscoroutine(call) else call
        except Exception as e:
            ok, err = False, repr(e)
            res = {"error": err}

        out = {"index": idx, "ok": ok, "step": {"tool": tool, "args": args}, "result": res}
        await self.bus.publish("exec/result", out, sender=self.name)

        # Also mirror a compact line to the console (ASCII-only)
        pretty = json.dumps({"ok": ok, "tool": tool, "args": args}, ensure_ascii=True)
        await self.bus.publish("comms/out", {"text": f"[Executor] {pretty}"}, sender=self.name)
        return out
