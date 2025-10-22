# C:\bots\ecosys\agents\worker_agent.py
from __future__ import annotations
import asyncio, json
from typing import Any, Dict, List, Optional
from .base_agent import BaseAgent

__all__ = ["WorkerAgent"]

# ---------- small helpers ----------

def _truncate(obj: Any, limit: int = 300) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "…"

def _format_weather_summary(res: Dict[str, Any]) -> Optional[str]:
    """
    Build a one-line human summary if result looks like weather.current output.
    """
    if not isinstance(res, dict) or not res.get("ok"):
        return None
    resolved = res.get("resolved") or {}
    current  = res.get("current") or {}
    if not (resolved and current):
        return None

    name    = resolved.get("name") or "Location"
    admin1  = resolved.get("admin1")
    country = resolved.get("country")
    place = name
    if admin1 and country:
        place = f"{name}, {admin1}, {country}"
    elif country:
        place = f"{name}, {country}"

    t    = current.get("time")
    temp = current.get("temperature_c")
    wind = current.get("windspeed_kmh")
    code = current.get("weathercode")

    bits: List[str] = []
    if t: bits.append(str(t))
    if temp is not None: bits.append(f"{temp}°C")
    if wind is not None: bits.append(f"wind {wind} km/h")
    if code is not None: bits.append(f"code {code}")

    tail = ", ".join(bits) if bits else ""
    return f"Weather @ {place}{(' — ' + tail) if tail else ''}"

# ---------- worker agent ----------

class WorkerAgent(BaseAgent):
    """
    AI-3: Worker
    - Listens on 'task/exec' and executes steps.
    - Prints each operation to 'ui/print'.
    - Emits 'worker/done' with {ok, note, result, error?, results[], plan?}.
    """

    async def run(self):
        await self.bus.publish("ui/print", {"text": f"{self.name}: Worker online."}, sender=self.name)

        async for env in self.bus.subscribe("task/exec"):
            job_id = env.job_id
            # Capture the full plan (if provided) and the steps to execute
            plan = env.payload.get("plan") or {}
            steps = env.payload.get("steps") or []
            results: List[Dict[str, Any]] = []

            if not isinstance(steps, list):
                steps = []

            ok = True
            error_text: Optional[str] = None
            last_result: Any = None
            human_note: Optional[str] = None

            for step in steps:
                stype = (step or {}).get("type")

                if stype == "reason":
                    note = (step or {}).get("description") or ""
                    if note:
                        await self.bus.publish("ui/print", {"text": f"[Worker] {note}"}, sender=self.name, job_id=job_id)
                    continue

                if stype == "tool":
                    tool = (step or {}).get("tool")
                    args = (step or {}).get("args") or {}
                    if not tool:
                        ok = False
                        error_text = "Tool step missing 'tool' name."
                        break

                    # Execute the tool safely via ToolRegistry
                    try:
                        result = await self._call_tool(tool, args)
                    except Exception as e:
                        result = {"ok": False, "error": f"{type(e).__name__}: {e}"}

                    last_result = result

                    # **Log the result for this step** (for later analysis or autofix)
                    result_entry: Dict[str, Any] = result if isinstance(result, dict) else {"result": result}
                    result_entry["tool"] = tool
                    results.append(result_entry)

                    # Show the call + short result
                    try:
                        args_json = json.dumps(args, ensure_ascii=False)
                    except Exception:
                        args_json = str(args)
                    await self.bus.publish(
                        "ui/print",
                        {"text": f"[Worker] {tool} {args_json} -> {_truncate(result, 260)}"},
                        sender=self.name,
                        job_id=job_id,
                    )

                    if not (isinstance(result, dict) and result.get("ok")):
                        ok = False
                        error_text = (result or {}).get("error") or "tool reported failure"
                        break

                    # Domain summary (weather)
                    if human_note is None:
                        w = _format_weather_summary(result)
                        if w:
                            human_note = w
                else:
                    await self.bus.publish(
                        "ui/print",
                        {"text": f"[Worker] Unknown step type: {stype!r}"},
                        sender=self.name,
                        job_id=job_id,
                    )
                    continue

            # Determine a human-readable note if none was set (using last_result)
            if human_note is None and last_result is not None:
                if isinstance(last_result, dict) and last_result.get("ok"):
                    human_note = _truncate(last_result, 260)
                elif isinstance(last_result, dict) and last_result.get("error"):
                    human_note = f"Error: {last_result.get('error')}"
                else:
                    human_note = "Completed."

            # **Prepare payload with full results and plan**
            payload: Dict[str, Any] = {"ok": ok}
            if human_note:
                payload["note"] = human_note
            if last_result is not None:
                payload["result"] = last_result
            if error_text:
                payload["error"] = error_text
            payload["results"] = results
            if plan:
                payload["plan"] = plan

            # **If a clipboard copy was performed, publish the copied text for TesterAgent**
            copied_text = None
            for r in results:
                if r.get("tool") == "clipboard.get_text" and isinstance(r.get("text"), str):
                    copied_text = r["text"]
                    break
            if copied_text is not None:
                await self.bus.publish("task/result", {"text": copied_text}, sender=self.name, job_id=job_id)

            # Publish the final result of this task/job
            await self.bus.publish("worker/done", payload, sender=self.name, job_id=job_id)

    # ---- Tool dispatch (defensive) ----

    async def _call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        t = self.tools

        # methods with (name, **args)
        for m in ("arun", "run", "call", "execute", "invoke", "dispatch"):
            fn = getattr(t, m, None)
            if not fn:
                continue
            try:
                if asyncio.iscoroutinefunction(fn):
                    return await fn(name, **args)
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, lambda: fn(name, **args))
            except TypeError:
                # maybe signature is (name, args)
                try:
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(None, lambda: fn(name, args))
                except Exception:
                    continue
            except Exception:
                continue

        # resolver returning a callable
        for r in ("resolve", "get", "lookup"):
            res = getattr(t, r, None)
            if not res:
                continue
            try:
                cal = res(name)
                if asyncio.iscoroutinefunction(cal):
                    return await cal(**args)
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, lambda: cal(**args))
            except Exception:
                continue

        # last resort: direct attribute
        cal = getattr(t, name.replace(".", "_"), None)
        if cal:
            if asyncio.iscoroutinefunction(cal):
                return await cal(**args)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: cal(**args))

        return {"ok": False, "error": f"tool not found: {name}"}
