# C:\bots\ecosys\agents\autofix_agent.py
from __future__ import annotations
import os, json, inspect, re
from .base_agent import BaseAgent

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ALIASES_PATH = os.path.join(ROOT, "configs", "arg_aliases.json")

def _load_aliases():
    try:
        with open(ALIASES_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _save_aliases(d):
    os.makedirs(os.path.dirname(ALIASES_PATH), exist_ok=True)
    tmp = ALIASES_PATH + ".tmp"
    with open(tmp, "w", encoding="ascii", errors="backslashreplace") as f:
        json.dump(d, f, ensure_ascii=True, indent=2)
        f.write("\n")
    os.replace(tmp, ALIASES_PATH)

class AutofixAgent(BaseAgent):
    """
    AI-6: Autofix
    - Listens for worker failures
    - If a tool throws ARG_ALIAS_NEEDED:<tool>:<badkw>, automatically adds a dynamic alias
      by mapping <badkw> to the most plausible parameter name on that tool.
    - This teaches the system without editing code; ToolRegistry reads aliases live.
    """
    async def run(self):
        await self.say("Autofix online.")
        async for env in self.bus.subscribe("worker/done"):
            job_id = env.job_id
            results = env.payload.get("results") or []
            plan = env.payload.get("plan") or {}
            changed = False

            for r in results:
                if r.get("ok", True): 
                    continue
                err = (r.get("error") or "")
                tool = r.get("tool") or ""
                if err.startswith("ARG_ALIAS_NEEDED:") and ":" in err:
                    _, tname, bad = err.split(":", 2)
                    bad = bad.strip()
                    tname = tname.strip()
                    # Inspect the registered tool function to find candidate params
                    tentry = self.tools._tools.get(tname) if hasattr(self.tools, "_tools") else None
                    fn = (tentry.get("fn") if isinstance(tentry, dict) else tentry)
                    if not callable(fn):
                        continue
                    try:
                        sig = inspect.signature(fn)
                        candidates = [p for p in sig.parameters.keys() if p not in ("self","danger")]
                    except Exception:
                        candidates = []
                    # Choose a likely target
                    target = None
                    preferred = ["path","src","dst","dir","directory","file","filename","content","text","code","command"]
                    for p in preferred:
                        if p in candidates:
                            target = p; break
                    if not target and candidates:
                        target = candidates[0]

                    if target:
                        aliases = _load_aliases()
                        if tname not in aliases:
                            aliases[tname] = {}
                        if aliases[tname].get(bad) != target:
                            aliases[tname][bad] = target
                            _save_aliases(aliases)
                            changed = True
                            await self.bus.publish("ui/print",
                                {"text": f"[Autofix] Learned arg alias for {tname}: '{bad}' -> '{target}'"},
                                sender=self.name, job_id=job_id)

            if changed:
                # Ask Brain to retry immediately with the same plan
                await self.bus.publish("task/retry", {"plan": plan, "feedback": "Autofix added arg aliases."},
                                       sender=self.name, job_id=job_id)
