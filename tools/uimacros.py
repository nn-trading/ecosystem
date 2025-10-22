# C:\bots\ecosys\tools\uimacros.py
from __future__ import annotations
from typing import Any, Dict
import os

DANGER = os.environ.get("AGENT_DANGER_MODE", "1") == "1"
tools = None  # filled in register()

def _call(name: str, **kwargs) -> Dict[str, Any]:
    fn = tools.get(name)
    if not fn:
        return {"ok": False, "error": f"tool not found: {name}"}
    try:
        return fn(**kwargs) if kwargs else fn()
    except TypeError:
        return fn(kwargs)

def notepad_type_copy(text: str = "123") -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    res = _call("sysctl.launch", exe="notepad")
    if not res.get("ok"):
        return res
    pid = res["pid"]
    s = _call("win.set_text_pid", pid=pid, text=text)
    if not s.get("ok"):
        return s
    c = _call("win.copy_pid", pid=pid)
    if not c.get("ok"):
        return c
    g = _call("win.get_text_pid", pid=pid)
    return {"ok": True, "pid": pid, "text": g.get("text", "")}

def paste_to_new_notepad() -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    res = _call("sysctl.launch", exe="notepad")
    if not res.get("ok"):
        return res
    pid2 = res["pid"]
    p2 = _call("win.paste_pid", pid=pid2)
    if not p2.get("ok"):
        return p2
    return {"ok": True, "pid": pid2, "text": p2.get("text", "")}

def register(_tools) -> None:
    global tools
    tools = _tools
    tools.add("macro.notepad_type_copy",     notepad_type_copy,   desc="Open Notepad, set text, copy to clipboard, verify via control text")
    tools.add("macro.paste_to_new_notepad",  paste_to_new_notepad,desc="Open a new Notepad and paste from clipboard via WM_PASTE, return resulting text")
