# C:\bots\ecosys\tools\shell.py
from __future__ import annotations
import subprocess, time
from typing import Any, Dict, Optional

def run(cmd: str, timeout: Optional[int] = None) -> Dict[str, Any]:
    try:
        c = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"ok": True, "code": c.returncode, "stdout": c.stdout, "stderr": c.stderr}
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error": f"timeout after {timeout}s", "stdout": e.stdout or "", "stderr": e.stderr or ""}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

def sleep(seconds: float) -> Dict[str, Any]:
    try:
        time.sleep(float(seconds))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

def register(tools) -> None:
    tools.add("shell.run", run, desc="Run a shell command and capture output")
    tools.add("shell.exec", run, desc="Run a shell command and capture output (alias)")
    tools.add("shell.sleep", sleep, desc="Sleep for a number of seconds")
