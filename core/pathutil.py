from __future__ import annotations
import os
import re
from typing import Tuple

# Windows-invalid characters for filenames
_INVALID_CHARS = set('<>:"/\\|?*')
_RESERVED_NAMES = {
    "CON","PRN","AUX","NUL",
    *{f"COM{i}" for i in range(1,10)},
    *{f"LPT{i}" for i in range(1,10)}
}
_MAX_NAME = 255  # typical max filename length

def _to_ascii(s: str) -> str:
    try:
        return s.encode("ascii", "ignore").decode("ascii", "ignore")
    except Exception:
        return "".join(ch for ch in s if ord(ch) < 128)

def sanitize_filename(name: str) -> str:
    """
    Return a Windows-safe, ASCII-only filename (no path separators).
    - Drops non-ASCII characters
    - Replaces invalid characters with underscore
    - Trims trailing dots/spaces
    - Avoids reserved device names
    - Ensures non-empty; falls back to "file" when empty
    """
    if not name:
        return "file"

    # Split extension, sanitize stem and extension separately
    stem, ext = os.path.splitext(name)
    stem_ascii = _to_ascii(stem)
    ext_ascii = _to_ascii(ext)

    # Replace invalid characters
    def _clean(part: str) -> str:
        out = []
        for ch in part:
            if ch in _INVALID_CHARS or ord(ch) < 32:
                out.append("_")
            else:
                out.append(ch)
        s = "".join(out)
        # Collapse runs of spaces/underscores
        s = re.sub(r"[\s_]+", "_", s)
        return s

    stem_clean = _clean(stem_ascii).strip(" .")
    ext_clean = _clean(ext_ascii)

    if not stem_clean:
        stem_clean = "file"

    # Avoid reserved names (case-insensitive)
    if stem_clean.upper() in _RESERVED_NAMES:
        stem_clean = f"_{stem_clean}"

    # Enforce length (leave room for extension)
    max_stem_len = max(1, _MAX_NAME - len(ext_clean))
    if len(stem_clean) > max_stem_len:
        stem_clean = stem_clean[:max_stem_len]

    safe = stem_clean + ext_clean
    if not safe:
        safe = "file"
    return safe

def sanitize_save_path(path: str) -> Tuple[str, bool]:
    """
    Sanitize only the final filename component of path. Returns (sanitized_path, changed?).
    Directories are kept as-is to avoid surprising relocations.
    """
    if not path:
        return path, False
    directory, name = os.path.split(path)
    safe_name = sanitize_filename(name)
    if name != safe_name:
        return os.path.join(directory, safe_name), True
    return path, False
