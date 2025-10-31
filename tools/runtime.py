# C:\bots\ecosys\tools\runtime.py
from __future__ import annotations
import os, sys, json, time, subprocess
from typing import Any, Dict, List, Optional

DANGER = os.environ.get("AGENT_DANGER_MODE", "0") == "1"


def _psutil():
    import importlib
    return importlib.import_module("psutil")


def list_children(parent_pid: Optional[int] = None, recursive: bool = True) -> Dict[str, Any]:
    try:
        psutil = _psutil()
        pid = int(parent_pid or os.getpid())
        try:
            proc = psutil.Process(pid)
        except Exception as e:
            return {"ok": False, "error": f"no such process {pid}: {e}"}
        kids = proc.children(recursive=bool(recursive))
        items = []
        for c in kids:
            try:
                items.append({
                    "pid": int(c.pid),
                    "name": c.name(),
                    "status": c.status(),
                    "cmdline": " ".join(c.cmdline() or [])
                })
            except Exception:
                items.append({"pid": int(c.pid)})
        return {"ok": True, "parent": pid, "count": len(items), "children": items}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def kill_pid(pid: int, tree: bool = False, timeout_sec: float = 3.0) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    try:
        psutil = _psutil()
        p = psutil.Process(int(pid))
        killed = []
        if tree:
            for ch in p.children(recursive=True):
                try:
                    ch.terminate()
                    killed.append(int(ch.pid))
                except Exception:
                    pass
        p.terminate()
        try:
            psutil.wait_procs([p], timeout=timeout_sec)
        except Exception:
            pass
        return {"ok": True, "pid": int(pid), "killed_children": killed}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def kill_children(parent_pid: Optional[int] = None, timeout_sec: float = 3.0) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    try:
        psutil = _psutil()
        pid = int(parent_pid or os.getpid())
        proc = psutil.Process(pid)
        killed = []
        for ch in proc.children(recursive=True):
            try:
                ch.terminate()
                killed.append(int(ch.pid))
            except Exception:
                pass
        try:
            psutil.wait_procs([psutil.Process(p) for p in killed], timeout=timeout_sec)
        except Exception:
            pass
        return {"ok": True, "parent": pid, "killed": killed, "count": len(killed)}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def list_procs(name_filter: Optional[str] = None) -> Dict[str, Any]:
    try:
        psutil = _psutil()
        items = []
        for p in psutil.process_iter(attrs=["pid", "name", "cmdline", "status"]):
            try:
                nm = p.info.get("name") or ""
                if name_filter and name_filter.lower() not in nm.lower():
                    continue
                items.append({
                    "pid": int(p.info.get("pid")),
                    "name": nm,
                    "status": p.info.get("status"),
                    "cmdline": " ".join(p.info.get("cmdline") or [])
                })
            except Exception:
                pass
        return {"ok": True, "count": len(items), "procs": items}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def soft_reboot(cmd: Optional[List[str]] = None, wait_sec: float = 0.5) -> Dict[str, Any]:
    """
    Attempt a Python-only soft reboot:
    - Spawns a replacement process (cmd or current interpreter with main.py)
    - Terminates current process after short delay
    Requires AGENT_DANGER_MODE=1.
    """
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    try:
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not cmd:
            # Default: relaunch this app via `python main.py`
            exe = sys.executable
            main_py = os.path.join(repo, "main.py")
            cmd = [exe, main_py]
        proc = subprocess.Popen(cmd, cwd=repo)
        # Give the new process time to initialize
        time.sleep(max(0.05, float(wait_sec)))
        os._exit(0)
    except SystemExit:
        raise
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def register(reg) -> None:
    reg.add("runtime.children", list_children, desc="List child processes for a parent pid (psutil)")
    reg.add("runtime.kill_pid", kill_pid, desc="Terminate a process (and optionally its tree) using psutil")
    reg.add("runtime.kill_children", kill_children, desc="Terminate all children of a parent process using psutil")
    reg.add("runtime.list_procs", list_procs, desc="List processes with optional name filter")
    reg.add("runtime.soft_reboot", soft_reboot, desc="Soft reboot the application by spawning a new process then exiting")
