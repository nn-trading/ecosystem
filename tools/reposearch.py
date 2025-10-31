# C:\bots\ecosys\tools\reposearch.py
from __future__ import annotations
import os, re, json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Iterable, Optional, Tuple

# Default text-like extensions; still check binary by sniffing
DEFAULT_EXTS = {
    ".py", ".ps1", ".cmd", ".bat", ".txt", ".md", ".json", ".yml", ".yaml",
    ".ini", ".cfg", ".toml", ".csv", ".tsv", ".sql", ".log"
}
DEFAULT_EXCLUDES = {".git", ".venv", "node_modules", "workspace\\logs", "logs", "var", "runs", "__pycache__"}


def _is_binary_bytes(chunk: bytes) -> bool:
    if not chunk:
        return False
    # Heuristic: NUL bytes or high ratio of non-text
    if b"\x00" in chunk:
        return True
    # Consider bytes outside common text range as binary if too many
    textish = sum(1 for b in chunk if 9 <= b <= 13 or 32 <= b <= 126)
    return (textish / max(1, len(chunk))) < 0.75


def _should_skip_dir(path: Path) -> bool:
    name = path.name.lower()
    if name in {x.lower() for x in DEFAULT_EXCLUDES}:
        return True
    # Skip large vendor/cache dirs by substring
    p = str(path).lower()
    return any(seg in p for seg in ("\\.git\\", "\\.venv\\", "node_modules\\", "\\workspace\\logs\\", "\\logs\\", "\\var\\", "\\runs\\", "\\__pycache__\\"))


def _iter_files(root: Path, exts: Optional[Iterable[str]]) -> Iterable[Path]:
    use_exts = {e.lower() for e in (exts or DEFAULT_EXTS)}
    for dp, dn, fnames in os.walk(root):
        dpp = Path(dp)
        if _should_skip_dir(dpp):
            # prune traversal by clearing dn
            dn[:] = []
            continue
        for fn in fnames:
            p = dpp / fn
            if use_exts:
                if p.suffix.lower() not in use_exts:
                    # Allow extensionless scripts
                    if "." in p.name:
                        continue
            yield p


@dataclass
class Match:
    path: str
    line: int
    col: int
    text: str


def repo_search(root: str, query: str, regex: bool = False, icase: bool = True, max_results: int = 1000,
                exts: Optional[List[str]] = None) -> Dict[str, Any]:
    try:
        r = Path(root)
        if not r.exists():
            return {"ok": False, "error": f"root not found: {root}"}
        flags = re.IGNORECASE if icase else 0
        pat = re.compile(query, flags) if regex else None
        out: List[Dict[str, Any]] = []
        for fp in _iter_files(r, exts):
            try:
                # quick binary sniff
                with open(fp, "rb") as bf:
                    head = bf.read(4096)
                if _is_binary_bytes(head):
                    continue
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        hay = line.rstrip("\n\r")
                        if pat is not None:
                            m = pat.search(hay)
                            if not m:
                                continue
                            col = m.start() + 1
                        else:
                            # literal contains
                            pos = hay.lower().find(query.lower()) if icase else hay.find(query)
                            if pos < 0:
                                continue
                            col = pos + 1
                        out.append({"path": str(fp), "line": i, "col": col, "text": hay[:400]})
                        if len(out) >= max_results:
                            return {"ok": True, "count": len(out), "results": out}
            except Exception:
                # ignore unreadable files
                continue
        return {"ok": True, "count": len(out), "results": out}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(tools) -> None:
    tools.add("repo.search", lambda root, query, regex=False, icase=True, max_results=1000: repo_search(root, query, regex=bool(regex), icase=bool(icase), max_results=int(max_results)),
              desc="Search repository files using Python (no FINDSTR). Args: root, query, [regex, icase, max_results]")
