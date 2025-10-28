# C:\bots\ecosys\tools\paths.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional


def paths_get(name: str, default: Optional[str] = None) -> Dict[str, Any]:
    try:
        if not isinstance(name, str) or not name:
            return {"ok": False, "error": "name required"}
        # Simple env/knowns resolver
        val = os.environ.get(name)
        if not val:
            if name.upper() == "HOME":
                val = os.path.expanduser("~")
            elif name.upper() == "TEMP":
                val = os.environ.get("TEMP") or os.environ.get("TMP") or os.path.expanduser("~")
            elif name.upper() == "DESKTOP":
                # Windows Desktop fallback
                home = os.path.expanduser("~")
                cand = os.path.join(home, "Desktop")
                val = cand if os.path.isdir(cand) else home
        if not val:
            val = default or ""
        return {"ok": bool(val), "name": name, "path": val}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(reg) -> None:
    reg.add("paths.get", paths_get, desc="Resolve common paths by name or env -> {ok,path}")
