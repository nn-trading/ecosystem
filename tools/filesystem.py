from __future__ import annotations
from pathlib import Path
import shutil
from core.pathutil import sanitize_save_path

def read(path: str) -> dict:
    p = Path(path)
    return {"ok": p.exists(), "path": str(p), "content": p.read_text(encoding="utf-8") if p.exists() else ""}

def write(path: str, content: str) -> dict:
    safe_path, changed = sanitize_save_path(path)
    p = Path(safe_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # If writing Markdown, ensure headings are ASCII-only
    if str(p).lower().endswith(".md"):
        lines = []
        for ln in (content or "").splitlines(True):
            if ln.lstrip().startswith("#"):
                try:
                    ln = ln.encode("ascii", "ignore").decode("ascii", "ignore")
                except Exception:
                    ln = "".join(ch for ch in ln if ord(ch) < 128)
            lines.append(ln)
        content_to_write = "".join(lines)
    else:
        content_to_write = content
    p.write_text(content_to_write, encoding='ascii', errors='ignore')
    return {"ok": True, "path": str(p), "bytes": len(content_to_write), "sanitized": changed}

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
    safe_dst, changed = sanitize_save_path(dst)
    s = Path(src); d = Path(safe_dst)
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s, d)
    return {"ok": True, "src": str(s), "dst": str(d), "sanitized": changed}

def move(src: str, dst: str) -> dict:
    safe_dst, changed = sanitize_save_path(dst)
    s = Path(src); d = Path(safe_dst)
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return {"ok": True, "src": str(s), "dst": str(d), "sanitized": changed}
