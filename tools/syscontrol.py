# C:\bots\ecosys\tools\syscontrol.py
from __future__ import annotations
import os, subprocess
from typing import Any, Dict, List, Optional


def _sanitize_exe(name: str) -> str:
    s = (name or "").strip().strip('"').strip("'")
    while s and s[-1] in ",.;:!?)":
        s = s[:-1]
    return s


def _resolve_exe(exe: str) -> str:
    x = _sanitize_exe(exe or "")
    xl = x.lower()
    if xl in ("notepad", "notepad.exe"):
        sysroot = os.environ.get("SystemRoot", r"C:\\Windows")
        cand = os.path.join(sysroot, "System32", "notepad.exe")
        if os.path.exists(cand):
            return cand
    return x


def launch(exe: str, args: Optional[List[str]] = None, cwd: Optional[str] = None) -> Dict[str, Any]:
    try:
        argv = list(args or [])
        cmd0 = _resolve_exe(exe)
        if not cmd0:
            cmd0 = _resolve_exe("notepad.exe")
        cmd = [cmd0] + argv
        proc = subprocess.Popen(
            cmd,
            cwd=cwd or None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x00000008,  # DETACHED_PROCESS
        )
        return {"ok": True, "pid": int(proc.pid), "exe": cmd0}
    except FileNotFoundError as e:
        try:
            # Fallback to Notepad if resolution failed
            np = _resolve_exe("notepad.exe")
            proc = subprocess.Popen([np], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000008)
            return {"ok": True, "pid": int(proc.pid), "exe": np, "fallback": True, "error": f"{e.__class__.__name__}: {e}"}
        except Exception as e2:
            return {"ok": False, "error": f"{e2.__class__.__name__}: {e2}"}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def register(tools) -> None:
    tools.add("sysctl.launch", launch, desc="Launch a Windows executable with optional args")
