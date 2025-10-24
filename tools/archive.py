from __future__ import annotations
from pathlib import Path
import zipfile, os
from typing import Dict, Any, Optional

# Internal helpers

def _zip_dir_impl(src: Path, zp: Path) -> Dict[str, Any]:
    if not src.exists() or not src.is_dir():
        return {"ok": False, "error": f"source dir not found: {src}"}
    zp.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src):
            for f in files:
                fp = Path(root) / f
                zf.write(fp, arcname=str(fp.relative_to(src)))
    return {"ok": True, "src_dir": str(src), "zip_path": str(zp)}


def _unzip_impl(zp: Path, dest: Path) -> Dict[str, Any]:
    if not zp.exists():
        return {"ok": False, "error": f"zip not found: {zp}"}
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp, "r") as zf:
        zf.extractall(dest)
    return {"ok": True, "zip_path": str(zp), "dest_dir": str(dest)}


# Backward-compatible direct functions (kept for imports/tests)

def zip_dir(src_dir: str, zip_path: str) -> dict:
    return _zip_dir_impl(Path(src_dir), Path(zip_path))


def unzip(zip_path: str, dest_dir: str) -> dict:
    return _unzip_impl(Path(zip_path), Path(dest_dir))


# Tool entry points accepting flexible argument names used by plans

def zip_dir_tool(
    path: Optional[str] = None,
    src: Optional[str] = None,
    src_dir: Optional[str] = None,
    dest: Optional[str] = None,
    zip_path: Optional[str] = None,
    out: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    s = src_dir or src or path
    if not s:
        return {"ok": False, "error": "missing source dir: provide path/src/src_dir"}
    src_p = Path(s)

    # Determine output path
    z = zip_path or dest or out
    if z:
        zp = Path(z)
        # If user passed a directory or a path without .zip, build filename
        if zp.suffix.lower() != ".zip":
            base = name or (src_p.name + ".zip")
            zp = zp / base
    else:
        # Default to alongside source dir
        zp = src_p.parent / ((name or src_p.name) + ".zip")

    return _zip_dir_impl(src_p, zp)


def unzip_tool(
    path: Optional[str] = None,
    zip_path: Optional[str] = None,
    src: Optional[str] = None,
    dest: Optional[str] = None,
    dest_dir: Optional[str] = None,
    out: Optional[str] = None,
) -> Dict[str, Any]:
    z = zip_path or path or src
    if not z:
        return {"ok": False, "error": "missing zip path: provide zip_path/path/src"}
    zp = Path(z)

    d = dest_dir or dest or out
    if d:
        dp = Path(d)
    else:
        # Default to folder with the same stem
        dp = zp.with_suffix("")
    return _unzip_impl(zp, dp)


def register(tools) -> None:
    tools.add("zip.zip_dir", zip_dir_tool, desc="Zip a directory to a .zip file. Args: path/src/src_dir, dest/zip_path/out, name")
    tools.add("zip.unzip", unzip_tool, desc="Unzip a .zip file. Args: zip_path/path/src, dest/dest_dir/out")
