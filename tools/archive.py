from __future__ import annotations
from pathlib import Path
import zipfile, os

def zip_dir(src_dir: str, zip_path: str) -> dict:
    src = Path(src_dir)
    zp = Path(zip_path)
    zp.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src):
            for f in files:
                fp = Path(root) / f
                zf.write(fp, arcname=str(fp.relative_to(src)))
    return {"ok": True, "src_dir": str(src), "zip_path": str(zp)}

def unzip(zip_path: str, dest_dir: str) -> dict:
    zp = Path(zip_path)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp, "r") as zf:
        zf.extractall(dest)
    return {"ok": True, "zip_path": str(zp), "dest_dir": str(dest)}
