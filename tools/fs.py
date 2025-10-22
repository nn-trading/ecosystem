# C:\bots\ecosys\tools\fs.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

def ls(path: str) -> Dict[str, Any]:
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

def register(tools) -> None:
    tools.add("fs.ls", ls, desc="List directory contents or single file info")
