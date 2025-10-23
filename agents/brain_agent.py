# C:\bots\ecosys\agents\brain_agent.py
from __future__ import annotations
import asyncio
import inspect
import re
from typing import Any, Dict, List

OPEN_RX = re.compile(r'\b(?:open|launch|start)\s+([^\s"].+?|\S+)(?:\s+(.*))?$', re.IGNORECASE)

def _extract_text(msg: Any) -> str:
    if msg is None:
        return ""
    if isinstance(msg, dict):
        for k in ("text","content","message","prompt","user_text"):
            v = msg.get(k)
            if isinstance(v, str):
                return v
        data = msg.get("data")
        if isinstance(data, dict):
            for k in ("text","content","message","prompt"):
                v = data.get(k)
                if isinstance(v, str):
                    return v
        return str(msg)
    for attr in ("text","content","message","prompt","user_text"):
        v = getattr(msg, attr, None)
        if isinstance(v, str):
            return v
    data = getattr(msg, "data", None)
    if isinstance(data, dict):
        for k in ("text","content","message","prompt"):
            v = data.get(k)
            if isinstance(v, str):
                return v
    payload = getattr(msg, "payload", None)
    if isinstance(payload, dict):
        for k in ("text","content","message","prompt"):
            v = payload.get(k)
            if isinstance(v, str):
                return v
    return str(msg)

def _parse_actions(text: str) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    t = (text or "")
    s = " " + t.lower() + " "

    typed_any = False
    has_select_all = False
    asked_copy  = (" paste " not in s) and ((" copy " in s) or ("ctrl+c" in s)) or (" then copy" in s)
    asked_paste = (" paste " in s) or ("ctrl+v" in s) or (" then paste" in s)

    # 1) type "quoted text"
    for m in re.finditer(r'\btype\s+[\"]([^\"]+)[\"]', t, flags=re.IGNORECASE):
        val = (m.group(1) or "").strip()
        if val:
            steps.append({"type": "tool", "tool": "ui.type_text", "args": {"text": val}})
            typed_any = True

    # 2) type exactly: <text>  OR  type: <text>
    m = re.search(r'\btype(?:\s+exactly)?\s*:\s*([^\r\n]+)', t, flags=re.IGNORECASE)
    if m:
        val = (m.group(1) or "").strip()
        val = re.split(r'\s+(?:then|and)\s+', val, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if val:
            steps.append({"type": "tool", "tool": "ui.type_text", "args": {"text": val}})
            typed_any = True

    # 3) type <word> (single token fallback)  skip 'exactly' and 'exactly:' and tokens ending with ':'
    for m in re.finditer(r'\btype\s+([^\s,;:]+)', t, flags=re.IGNORECASE):
        val = (m.group(1) or "").strip().strip('"').strip("'").rstrip(":")
        if not val:
            continue
        if val.lower() == "exactly":
            continue
        steps.append({"type": "tool", "tool": "ui.type_text", "args": {"text": val}})
        typed_any = True

    # ctrl+<key> combos
    for m in re.finditer(r'\bctrl\+([a-z])\b', t, flags=re.IGNORECASE):
        key = m.group(1).lower()
        steps.append({"type": "tool", "tool": "ui.hotkey", "args": {"keys": ["ctrl", key]}})
        if key == "a":
            has_select_all = True

    if " select all " in s:
        steps.append({"type": "tool", "tool": "ui.hotkey", "args": {"keys": ["ctrl", "a"]}})
        has_select_all = True
    if " press enter " in s:
        steps.append({"type": "tool", "tool": "ui.hotkey", "args": {"keys": ["enter"]}})

    if asked_copy:
        steps.append({"type": "tool", "tool": "clipboard.clear", "args": {}})
        if typed_any and not has_select_all:
            steps.append({"type": "tool", "tool": "ui.hotkey", "args": {"keys": ["ctrl", "a"]}})
        steps.append({"type": "tool", "tool": "ui.hotkey", "args": {"keys": ["ctrl", "c"]}})
        steps.append({"type": "tool", "tool": "clipboard.get_text", "args": {}})

    if asked_paste and not asked_copy:
        steps.append({"type": "tool", "tool": "uimacros.paste_clipboard", "args": {}})

    return steps
class BrainAgent:
    def __init__(self, name: str, bus: Any, llm: Any, memory: Any, tools: Any):
        self.name = name
        self.bus = bus
        self.llm = llm
        self.memory = memory
        self.tools = tools

    async def _call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        reg = self.tools
        for meth in ("call","invoke","run","exec","execute","apply"):
            fn = getattr(reg, meth, None)
            if fn:
                try:
                    sig = inspect.signature(fn)
                    if "args" in sig.parameters and len(sig.parameters) == 2:
                        res = fn(tool_name, args)
                    else:
                        res = fn(tool_name, **args)
                    if inspect.isawaitable(res):
                        return await res
                    return res
                except Exception:
                    pass
        get = getattr(reg, "get", None)
        if callable(get):
            try:
                tool_fn = get(tool_name)
                if tool_fn:
                    res = tool_fn(**args)
                    if inspect.isawaitable(res):
                        return await res
                    return res
            except Exception:
                pass
        try:
            tool_fn = reg[tool_name]  # type: ignore[index]
            res = tool_fn(**args)
            if inspect.isawaitable(res):
                return await res
            return res
        except Exception as e:
            return {"ok": False, "error": f"tool '{tool_name}' not callable: {e}"}

    def _plan_for_text(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {
                "title": "Fallback Plan",
                "rationale": "Empty message; inspect workspace",
                "steps": [
                    {"type": "reason", "description": "No text provided; inspecting workspace"},
                    {"type": "tool", "tool": "fs.ls", "args": {"path": "C:/bots/ecosys"}},
                ],
            }
        m = OPEN_RX.search(text)
        if m:
            exe  = m.group(1).strip().strip('"').strip("'")
            tail = (m.group(2) or "").strip()
            steps: List[Dict[str, Any]] = [{"type": "tool", "tool": "sysctl.launch", "args": {"exe": exe, "args": []}}]
            steps.extend(_parse_actions(tail))
            title = f"Launch {exe}" + (f" and actions: {tail}" if tail else "")
            return {"title": title, "rationale": "Launch then execute UI actions.", "steps": steps}
        actions = _parse_actions(text)
        if actions:
            return {"title": "UI Actions", "rationale": "Execute requested UI keystrokes.", "steps": actions}
        return {
            "title": "Fallback Plan",
            "rationale": "No explicit tool match; inspecting workspace",
            "steps": [
                {"type": "reason", "description": "No tool matched; inspecting workspace"},
                {"type": "tool", "tool": "fs.ls", "args": {"path": "C:/bots/ecosys"}},
            ],
        }

    async def _emit_result_text(self, text: str) -> None:
        text = (text or "").rstrip("\r\n")
        payload = {"text": text}
        for meth in ("emit","publish","send"):
            fn = getattr(self.bus, meth, None)
            if fn:
                res = fn("task/result", payload, sender=self.name)  # type: ignore
                if inspect.isawaitable(res):
                    await res
                break
        print(f"{self.name}: clipboard => {text!r}")

    async def _execute_plan_steps(self, plan: Dict[str, Any]) -> None:
        last_pid = None
        last_exe = None
        steps: List[Dict[str, Any]] = plan.get("steps", [])
        for step in steps:
            if step.get("type") != "tool":
                continue
            tool = step.get("tool")
            args = step.get("args", {}) or {}

            if tool == "sysctl.launch":
                last_exe = (args.get("exe") or "").strip().lower()
                res = await self._call_tool(tool, args)
                if isinstance(res, dict):
                    last_pid = res.get("pid")
                # Always try to focus the app we just opened
                activated = False
                if last_pid:
                    a = await self._call_tool("win.activate_pid", {"pid": int(last_pid)})
                    activated = isinstance(a, dict) and a.get("ok") is True
                if not activated:
                    # Single-instance apps (like Win11 Notepad) need a title-based fallback
                    hint = "Notepad" if ("notepad" in (last_exe or "")) else (last_exe.split("\\")[-1].split(".")[0] or "Notepad")
                    await self._call_tool("win.activate_title_contains", {"substr": hint})
                await asyncio.sleep(1.0)  # give it a moment to focus
                continue

            # small pacing for UI/macros
            if tool.startswith("ui.") or tool.startswith("uimacros."):
                await asyncio.sleep(0.20)

            if tool == "clipboard.get_text":
                await asyncio.sleep(0.25)
                res = await self._call_tool(tool, args)
                if isinstance(res, dict) and res.get("ok"):
                    await self._emit_result_text(str(res.get("text", "")))
                continue

            await self._call_tool(tool, args)

    # --------- UPDATED: Plan method delegates execution to WorkerAgent ----------
    async def plan(self, msg: Any) -> Dict[str, Any]:
        text = _extract_text(msg)
        plan = self._plan_for_text(text)
        # Determine job ID from incoming message (for tracking across agents)
        job_id = getattr(msg, "job_id", None) or (msg.get("job_id") if isinstance(msg, dict) else None)
        # Publish the plan for logging and TesterAgent to examine
        await self.bus.publish("task/plan", plan, sender=self.name, job_id=job_id)
        # Hand off execution of the plan's steps to the WorkerAgent (AI-3)
        await self.bus.publish("task/exec", {"steps": plan.get("steps", [])}, sender=self.name, job_id=job_id)
        return plan

    # --------- UPDATED: Run method adds retry handler and uses bus.on ----------
    async def run(self) -> None:
        try:
            on = getattr(self.bus, "on", None)
            if callable(on):
                # Existing handler for new user tasks
                async def _handler(msg: Any) -> None:
                    await self.plan(msg)
                r1 = on("task/new", _handler)

                # **Handler for retry (auto-fix) events**
                async def _retry_handler(msg: Any) -> None:
                    # If a plan is provided in the retry message (from AutofixAgent), reuse it
                    plan = None
                    feedback = None
                    if isinstance(msg, dict):
                        plan = msg.get("data", {}).get("plan")
                        feedback = msg.get("data", {}).get("feedback")
                    if plan:
                        job_id = msg.get("job_id") if isinstance(msg, dict) else getattr(msg, "job_id", None)
                        # Inform via UI that an autofix is being applied (optional)
                        if feedback:
                            await self.bus.publish(
                                "ui/print",
                                {"text": f"{self.name}: (Autofix) {feedback}"},
                                sender=self.name, job_id=job_id
                            )
                        # Re-publish the plan and its steps for execution
                        await self.bus.publish("task/plan", plan, sender=self.name, job_id=job_id)
                        await self.bus.publish("task/exec", {"steps": plan.get("steps", [])}, sender=self.name, job_id=job_id)
                    else:
                        # No plan provided – treat it like a new task
                        await self.plan(msg)

                r2 = on("task/retry", _retry_handler)

                # Await handlers if needed (for asynchronous on() implementations)
                if inspect.isawaitable(r1): await r1
                if inspect.isawaitable(r2): await r2
        except Exception:
            return
