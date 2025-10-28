# C:\bots\ecosys\core\ascii_writer.py
from __future__ import annotations
import os, json
from typing import Tuple, Dict, Any

from .pathutil import sanitize_save_path


def to_ascii(text: str) -> str:
    try:
        return text.encode("ascii", "ignore").decode("ascii", "ignore")
    except Exception:
        return "".join(ch for ch in str(text) if ord(ch) < 128)


def _ensure_parent(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def write_text_ascii(path: str, text: str) -> str:
    """Write ASCII-only text to path, sanitizing filename. Returns final path."""
    spath, _ = sanitize_save_path(path)
    _ensure_parent(spath)
    with open(spath, "w", encoding="ascii", errors="ignore") as f:
        f.write(to_ascii(text))
    return spath


def write_jsonl_ascii(path: str, obj: Dict[str, Any]) -> str:
    """Append one ASCII-safe JSON line to path. Returns final path."""
    spath, _ = sanitize_save_path(path)
    _ensure_parent(spath)
    line = json.dumps(obj, ensure_ascii=True) + "\n"
    with open(spath, "a", encoding="ascii", errors="ignore") as f:
        f.write(line)
    return spath
