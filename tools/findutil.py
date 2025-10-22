from __future__ import annotations
from pathlib import Path
import re

def grep(root: str, pattern: str, max_matches: int = 2000) -> dict:
    base = Path(root)
    if not base.exists():
        return {"ok": False, "error": "root not found", "root": str(base)}
    rx = re.compile(pattern, re.IGNORECASE)
    matches = []
    for p in base.rglob("*"):
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for m in rx.finditer(text):
                    s = m.start()
                    snippet = text[max(0, s-80): s+120]
                    matches.append({"file": str(p), "offset": s, "snippet": snippet})
                    if len(matches) >= max_matches:
                        return {"ok": True, "matches": matches, "truncated": True}
            except Exception:
                continue
    return {"ok": True, "matches": matches}
