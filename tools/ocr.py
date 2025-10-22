# C:\bots\ecosys\tools\ocr.py
from __future__ import annotations
import os
from typing import Dict, Any, Optional

def _find_tesseract() -> Optional[str]:
    # 1) Respect env override
    t = os.environ.get("TESSERACT_EXE")
    if t and os.path.isfile(t):
        return t
    # 2) Common Windows installs
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def _need_deps():
    try:
        import pytesseract  # noqa
        from PIL import Image  # noqa
    except Exception as e:
        raise RuntimeError("OCR deps missing. Run inside your venv: pip install pillow pytesseract") from e

def image(path: str, lang: str = "eng") -> Dict[str, Any]:
    """
    OCR an image file to text.
    If Tesseract is installed but not on PATH, set env TESSERACT_EXE to its full path.
    """
    _need_deps()
    import pytesseract
    from PIL import Image

    tpath = _find_tesseract()
    if not tpath:
        return {"ok": False,
                "error": ("Tesseract binary not found. Install it (winget install --id Tesseract-OCR.Tesseract -e) "
                          "or set env TESSERACT_EXE to its full path, e.g. "
                          r'"C:\Program Files\Tesseract-OCR\tesseract.exe"')}
    pytesseract.pytesseract.tesseract_cmd = tpath

    if not os.path.exists(path):
        return {"ok": False, "error": f"file not found: {path}"}
    try:
        img = Image.open(path)
        txt = pytesseract.image_to_string(img, lang=lang)
        return {"ok": True, "path": path, "lang": lang, "text": txt, "tesseract": tpath}
    except Exception as e:
        return {"ok": False, "error": f"OCR failed: {e}", "tesseract": tpath}
