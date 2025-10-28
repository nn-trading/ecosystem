# C:\bots\ecosys\core\tools.py
# NOTE: ToolRegistry now supports central tracing via set_tracer(callable)

from __future__ import annotations

import importlib
import traceback
from typing import Any, Dict, Callable, Optional, List

# ---------- Minimal registry ----------
class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tracer: Optional[Callable[[str, Dict[str, Any]], None]] = None

    def set_tracer(self, tracer: Optional[Callable[[str, Dict[str, Any]], None]]) -> None:
        self._tracer = tracer

    def add(self, name: str, fn: Callable[..., Dict[str, Any]], desc: str = "") -> None:
        self._tools[name] = {"fn": fn, "desc": desc}

    def call(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            # Shims ensure critical names always exist so Brain doesn’t stall
            if name == "sysctl.set_env":
                self.add("sysctl.set_env", _shim_set_env, "Set env (shim)")
                tool = self._tools[name]
            elif name == "sysctl.launch":
                self.add("sysctl.launch", _shim_launch, "Launch exe (shim)")
                tool = self._tools[name]
            elif name == "shell.run":
                self.add("shell.run", _shim_shell_run, "Shell run (shim)")
                tool = self._tools[name]
            elif name == "fs.ls":
                self.add("fs.ls", _shim_fs_ls, "List directory (shim)")
                tool = self._tools[name]
            else:
                return {"ok": False, "error": f"tool not found: {name}"}
        try:
            if self._tracer:
                try:
                    self._tracer("tool/call", {"tool": name, "args": kwargs})
                except Exception:
                    pass
            res = tool["fn"](**kwargs)
            if self._tracer:
                try:
                    self._tracer("tool/result", {"tool": name, "result": res})
                except Exception:
                    pass
            if not isinstance(res, dict):
                return {"ok": False, "error": f"tool {name} returned non-dict"}
            return res
        except Exception as e:
            return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

    def list(self) -> Dict[str, str]:
        return {k: v.get("desc", "") for k, v in self._tools.items()}

    def available(self) -> List[str]:
        return sorted(self._tools.keys())

# Singleton registry
REGISTRY = ToolRegistry()

def _safe_register(modname: str) -> None:
    try:
        mod = importlib.import_module(modname)
        if hasattr(mod, "register"):
            mod.register(REGISTRY)
    except Exception:
        print(f"[tools] failed to import {modname}:\n{traceback.format_exc()}")

# Wire tool modules
for _m in (
    "tools.shell",
    "tools.clipboard",
    "tools.ui",
    "tools.syscontrol",
    "tools.winui",
    "tools.winui_pid",
    "tools.fs",
    "tools.memutil",
    "tools.powershell",
    "tools.python_exec",
    "tools.archive",
    "tools.http",
    "tools.weather",
    "tools.webfetch",
    "tools.currency",
    "tools.calc",
    "tools.paths",
    "tools.uia",
    "tools.uimacros",
    "tools.schedule",
    "tools.browser",
):
    _safe_register(_m)

# ---------- Shims (safety net) ----------
import os, shutil, subprocess
from pathlib import Path

def _shim_set_env(name: str, value: str) -> Dict[str, Any]:
    os.environ[name] = value
    return {"ok": True, "name": name, "value": value}

def _shim_launch(exe: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    args = args or []
    try:
        resolved = exe
        if not Path(resolved).exists():
            cand = shutil.which(resolved) or (shutil.which(resolved + ".exe") if not resolved.lower().endswith(".exe") else None)
            if cand:
                resolved = cand
        if not resolved:
            return {"ok": False, "error": f"executable not found: {exe}"}
        proc = subprocess.Popen([resolved, *args], creationflags=subprocess.CREATE_NEW_CONSOLE)
        return {"ok": True, "exe": resolved, "args": args, "pid": proc.pid}
    except FileNotFoundError:
        return {"ok": False, "error": f"executable not found: {exe} (resolved: {resolved})"}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

def _shim_shell_run(cmd: str, timeout: Optional[int] = None) -> Dict[str, Any]:
    try:
        c = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"ok": True, "code": c.returncode, "stdout": c.stdout, "stderr": c.stderr}
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error": f"timeout after {timeout}s", "stdout": e.stdout or "", "stderr": e.stderr or ""}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

def _shim_fs_ls(path: str) -> Dict[str, Any]:
    try:
        p = Path(path)
        if not p.exists():
            return {"ok": False, "error": f"not found: {path}"}
        if p.is_dir():
            items = []
            for c in p.iterdir():
                items.append({"name": c.name, "is_dir": c.is_dir(), "size": c.stat().st_size})
            return {"ok": True, "path": str(p), "items": items}
        else:
            s = p.stat()
            return {"ok": True, "path": str(p), "items": [{"name": p.name, "is_dir": False, "size": s.st_size}]}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

# Ensure these names exist at startup
if "sysctl.set_env" not in REGISTRY._tools:
    REGISTRY.add("sysctl.set_env", _shim_set_env, desc="Set env (shim)")
if "sysctl.launch" not in REGISTRY._tools:
    REGISTRY.add("sysctl.launch", _shim_launch, desc="Launch exe (shim)")
if "shell.run" not in REGISTRY._tools:
    REGISTRY.add("shell.run", _shim_shell_run, desc="Shell run (shim)")
if "fs.ls" not in REGISTRY._tools:
    REGISTRY.add("fs.ls", _shim_fs_ls, desc="List directory (shim)")
