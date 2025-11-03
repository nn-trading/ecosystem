# dev/snapshot_core.py
from __future__ import annotations
import os, json
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT/"runs"
SRC_DIRS = [ROOT/"reports", ROOT/"artifacts"]

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def list_files(base: Path):
    out = []
    for p in base.rglob("*"):
        if p.is_file():
            try:
                out.append({"path": str(p.relative_to(base)), "bytes": p.stat().st_size})
            except Exception:
                out.append({"path": str(p), "bytes": -1})
    return out

def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    snap = RUNS/("core_snapshot_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    snap.mkdir(parents=True, exist_ok=True)
    summary = {"ts": now(), "dest": str(snap), "copied": []}
    for src in SRC_DIRS:
        if src.exists():
            dest = snap/src.name
            try:
                shutil.copytree(src, dest, dirs_exist_ok=True)
                summary["copied"].append(src.name)
            except Exception as e:
                (snap/"errors.txt").write_text(f"copy {src} failed: {e}\n", encoding="utf-8")
        else:
            summary["copied"].append(f"{src.name}:missing")
    (snap/"SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [f"SNAPSHOT {now()}", f"DEST {snap}"]
    for name in ("reports","artifacts"):
        p = snap/name
        if p.exists():
            lines.append(f"DIR {name}")
            for f in list_files(p):
                lines.append(f" - {f['path']} ({f['bytes']} bytes)")
        else:
            lines.append(f"DIR {name} missing")
    (snap/"SNAPSHOT.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(str(snap))

if __name__ == "__main__":
    main()
