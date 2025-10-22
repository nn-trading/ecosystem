from __future__ import annotations
from typing import Optional, List
import os
from core.pathutil import sanitize_save_path

try:
    from mss import mss
    from PIL import Image
except Exception as e:
    mss = None
    Image = None

VALID_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

def capture(path: str, region: Optional[List[int]] = None) -> dict:
    if mss is None or Image is None:
        return {"ok": False, "error": "mss/Pillow not available. pip install mss pillow"}

    if not path:
        return {"ok": False, "error": "no path provided"}

    # Clean up path and ensure extension
    p = path.strip().strip('"\'. ')
    root, ext = os.path.splitext(p)
    ext_low = ext.lower()

    if ext_low not in VALID_EXTS:
        # If no/invalid ext, default to .png
        p = (root or p).rstrip(". ") + ".png"
        ext_low = ".png"

    try:
        _ensure_dir(p)
        with mss() as sct:
            # Monitor 0 = all monitors (virtual), 1 = primary
            if region and len(region) == 4:
                left, top, width, height = [int(x) for x in region]
                mon = {"left": left, "top": top, "width": width, "height": height}
                shot = sct.grab(mon)
            else:
                # full virtual screen
                shot = sct.grab(sct.monitors[0])

            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            # Sanitize final filename to enforce ASCII-only
            p, sanitized = sanitize_save_path(p)
            img.save(p)
            return {"ok": True, "path": p, "width": shot.width, "height": shot.height, "sanitized": sanitized}
    except Exception as e:
        return {"ok": False, "error": str(e)}
