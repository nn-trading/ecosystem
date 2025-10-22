from __future__ import annotations
from pathlib import Path
import shutil

def read(path: str) -> dict:
    p = Path(path)
    return {"ok": p.exists(), "path": str(p), "content": p.read_text(encoding="utf-8") if p.exists() else ""}

def write(path: str, content: str) -> dict:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(p), "bytes": len(content)}

def ls(path: str) -> dict:
    p = Path(path)
    items = []
    if p.exists():
        for child in p.iterdir():
            try:
                items.append({"name": child.name, "is_dir": child.is_dir(), "size": child.stat().st_size})
            except Exception:
                items.append({"name": child.name, "is_dir": child.is_dir(), "size": None})
    return {"ok": p.exists(), "path": str(p), "items": items}

def mkdir(path: str) -> dict:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": str(p)}

def copy(src: str, dst: str) -> dict:
    s = Path(src); d = Path(dst)
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s, d)
    return {"ok": True, "src": str(s), "dst": str(d)}

def move(src: str, dst: str) -> dict:
    s = Path(src); d = Path(dst)
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return {"ok": True, "src": str(s), "dst": str(d)}
