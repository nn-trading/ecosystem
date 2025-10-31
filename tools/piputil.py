from __future__ import annotations
import os, sys, subprocess


def install(package: str, danger: bool = False) -> dict:
    """
    Install a pip package into the current venv.
    - If AGENT_DANGER_MODE=1 (or danger=True) we allow installation.
    - Otherwise refuse for safety.
    """
    if not package or not package.strip():
        return {"ok": False, "error": "no package provided"}

    allow_all = danger or os.environ.get("AGENT_DANGER_MODE", "0") == "1"
    if not allow_all:
        return {"ok": False, "error": "danger_mode off: pip install disabled"}

    cmd = [sys.executable, "-m", "pip", "install", package]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, shell=False, timeout=900)
        return {
            "ok": p.returncode == 0,
            "code": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "cmd": " ".join(cmd),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def register(reg) -> None:
    reg.add("pip.install", install, desc="Install a pip package into current environment (gated by AGENT_DANGER_MODE)")
