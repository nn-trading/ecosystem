# C:\bots\ecosys\tools\fs.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import shutil, hashlib

# Re-export higher-level filesystem helpers to provide user-friendly aliases
try:
    from .filesystem import read as _fs_read, write as _fs_write, mkdir as _fs_mkdir, copy as _fs_copy, move as _fs_move
except Exception:
    _fs_read = _fs_write = _fs_mkdir = _fs_copy = _fs_move = None  # type: ignore


def ls(path: str) -> Dict[str, Any]:
    try:
        p = Path(path)
        if not p.exists():
            return {"ok": False, "error": f"not found: {path}"}
        if p.is_dir():
            items = []
            for c in p.iterdir():
                try:
                    size = c.stat().st_size
                except Exception:
                    size = None
                items.append({"name": c.name, "is_dir": c.is_dir(), "size": size})
            return {"ok": True, "path": str(p), "items": items}
        else:
            s = p.stat()
            return {"ok": True, "path": str(p), "items": [{"name": p.name, "is_dir": False, "size": s.st_size}]}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def read(path: str) -> Dict[str, Any]:
    if _fs_read is None:
        return {"ok": False, "error": "filesystem helper missing"}
    return _fs_read(path)


def write(path: str, content: str) -> Dict[str, Any]:
    if _fs_write is None:
        return {"ok": False, "error": "filesystem helper missing"}
    return _fs_write(path, content)


def mkdir(path: str) -> Dict[str, Any]:
    if _fs_mkdir is None:
        return {"ok": False, "error": "filesystem helper missing"}
    return _fs_mkdir(path)


def copy(src: str, dst: str) -> Dict[str, Any]:
    if _fs_copy is None:
        return {"ok": False, "error": "filesystem helper missing"}
    return _fs_copy(src, dst)


def move(src: str, dst: str) -> Dict[str, Any]:
    if _fs_move is None:
        return {"ok": False, "error": "filesystem helper missing"}
    return _fs_move(src, dst)


def rm(path: str) -> Dict[str, Any]:
    try:
        p = Path(path)
        if not p.exists():
            return {"ok": True, "path": str(p), "removed": False}
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=False)
        else:
            p.unlink()
        return {"ok": True, "path": str(p), "removed": True}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def sha256(path: str) -> Dict[str, Any]:
    try:
        p = Path(path)
        h = hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return {"ok": True, "path": str(p), "sha256": h.hexdigest()}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def mv(src: str, dst: str) -> Dict[str, Any]:
    return move(src, dst)


def zip_dir(src_dir: str, dst_zip: str) -> Dict[str, Any]:
    try:
        # late import to avoid cycles
        import zipfile, os
        src = Path(src_dir)
        dst = Path(dst_zip)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dst, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(src):
                for fn in files:
                    fp = Path(root) / fn
                    z.write(fp, arcname=str(fp.relative_to(src)))
        return {"ok": True, "zip": str(dst)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(tools) -> None:
    tools.add("fs.ls", ls, desc="List directory contents or single file info")
    tools.add("fs.read", read, desc="Read a text file (utf-8)")
    tools.add("fs.write", write, desc="Write a text file (utf-8, Markdown headings ASCII-only)")
    tools.add("fs.mkdir", mkdir, desc="Create directory (parents ok)")
    tools.add("fs.copy", copy, desc="Copy file")
    tools.add("fs.move", move, desc="Move/rename file")
    tools.add("fs.mv", mv, desc="Move/rename file (alias)")
    tools.add("fs.rm", rm, desc="Remove file or directory recursively")
    tools.add("fs.sha256", sha256, desc="Compute SHA-256 of a file")
    tools.add("fs.zip", zip_dir, desc="Zip a directory into a .zip archive")
