# C:\bots\ecosys\core\autoacquire.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional

# AutoAcquire budget (per-process)
_ACQUIRE_COUNT = 0


def _danger_ok() -> bool:
    return os.environ.get("AGENT_DANGER_MODE", "0") == "1"


def _quota_ok() -> bool:
    try:
        max_ops = int(os.environ.get("AUTOACQUIRE_MAX", "2"))
    except Exception:
        max_ops = 2
    return _ACQUIRE_COUNT < max_ops


def _mark_used() -> None:
    global _ACQUIRE_COUNT
    _ACQUIRE_COUNT += 1


def _imports_ok(imports: List[str]) -> bool:
    for mod in imports:
        try:
            __import__(mod)
        except Exception:
            return False
    return True


def _post_install(reg, spec: Dict[str, Any]) -> Optional[str]:
    # Supported post-install spec:
    # {"type": "shell", "cmd": "python -m playwright install chromium", "timeout": 900}
    if not spec:
        return None
    typ = spec.get("type")
    if typ == "shell":
        cmd = spec.get("cmd")
        if not cmd:
            return None
        timeout = int(spec.get("timeout", 900))
        try:
            res = reg.call("shell.run", cmd=cmd, timeout=timeout)
            if not (isinstance(res, dict) and res.get("ok")):
                return f"post_install failed: {res}"
        except Exception as e:
            return f"post_install error: {e}"
    return None


def ensure_for_tool(reg, tool_name: str) -> Dict[str, Any]:
    """
    Ensure dependencies for a tool are present using TOOL_DESCRIPTORS.
    Safety:
    - Requires AGENT_DANGER_MODE=1 for any installs.
    - Enforces AUTOACQUIRE_MAX quota (default 2 installs per process).
    """
    try:
        from core.tools import TOOL_DESCRIPTORS
    except Exception:
        return {"ok": True, "note": "no descriptors available"}

    # Resolve descriptor (exact match, then wildcard prefix like 'browser.*')
    d = TOOL_DESCRIPTORS.get(tool_name)
    if not d:
        prefix = tool_name.split(".")[0] + ".*"
        d = TOOL_DESCRIPTORS.get(prefix)
    if not d:
        return {"ok": True, "note": "no requirements for tool"}

    requires: List[str] = list(d.get("requires", []))
    imports: List[str] = list(d.get("imports", []))
    posts: List[Dict[str, Any]] = list(d.get("post_install", []))

    # If already satisfied, nothing to do
    if imports and _imports_ok(imports):
        return {"ok": True, "note": "already satisfied"}

    # Safety gating
    if not _danger_ok():
        return {"ok": False, "error": f"autoacquire blocked: enable AGENT_DANGER_MODE=1 for {tool_name}"}
    if not _quota_ok():
        return {"ok": False, "error": "autoacquire quota exceeded"}

    # Perform installations
    for pkg in requires:
        try:
            r = reg.call("pip.install", package=pkg)
        except TypeError:
            r = reg.call("pip.install", package=pkg)  # fallback
        except Exception as e:
            return {"ok": False, "error": f"pip.install error: {e}"}
        if not (isinstance(r, dict) and r.get("ok")):
            return {"ok": False, "error": f"pip install failed for {pkg}: {r}"}
        # Log tool acquisition
        try:
            from memory.logger_db import get_logger_db
            get_logger_db().add_tool(name=pkg, version=None, provider="pip", meta={"tool": tool_name})
        except Exception:
            pass
        _mark_used()

    # Post-install steps (e.g., playwright browsers)
    for spec in posts:
        err = _post_install(reg, spec)
        if err:
            return {"ok": False, "error": err}

    # Verify imports after install
    if imports and not _imports_ok(imports):
        return {"ok": False, "error": f"dependencies still missing for {tool_name}: {imports}"}

    # Optional: record a skill
    try:
        from memory.logger_db import get_logger_db
        caps = d.get("capabilities") or []
        skill_title = f"AutoAcquire: {tool_name}"
        body = f"Installed packages: {', '.join(requires)}; caps: {', '.join(caps)}"
        get_logger_db().add_skill(skill_title, body)
    except Exception:
        pass

    return {"ok": True, "acquired": requires or []}
