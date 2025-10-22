# C:\bots\ecosys\tools\pdfutil.py
from __future__ import annotations
import os
from typing import Optional, Dict, Any, List

def _need_deps():
    try:
        import PyPDF2  # noqa
    except Exception as e:
        raise RuntimeError("PyPDF2 missing. Run: pip install pypdf2") from e

def extract_text(path: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
    _need_deps()
    import PyPDF2
    if not os.path.exists(path):
        return {"ok": False, "error": f"file not found: {path}"}
    out: List[str] = []
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            pages = len(reader.pages)
            lim = pages if max_pages is None else min(pages, max_pages)
            for i in range(lim):
                try:
                    out.append(reader.pages[i].extract_text() or "")
                except Exception:
                    out.append("")
        return {"ok": True, "pages": len(out), "text": "\n".join(out)}
    except Exception as e:
        return {"ok": False, "error": f"pdf read failed: {e}"}
