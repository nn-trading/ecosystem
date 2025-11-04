# dev/db_unify_summary.py (ASCII-only)
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REP = ROOT/"reports"

def read_json(p:Path):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception:
        return None

def main():
    dbh = read_json(REP/"db_health.json") or {}
    dbs = read_json(REP/"db_stats.json") or {}
    dbsnap = read_json(REP/"db_snapshot.json") or {}
    out = {
        "db_path": dbh.get("db_path") or dbs.get("db_path"),
        "health_ok": bool(dbh.get("ok")),
        "stats_exists": bool(dbs.get("exists")),
        "size_bytes": dbs.get("size_bytes"),
        "snapshot_dir": (dbsnap.get("snapshot") if isinstance(dbsnap, dict) else None),
        "copied": (dbsnap.get("copied") if isinstance(dbsnap, dict) else []),
        "missing": (dbsnap.get("missing") if isinstance(dbsnap, dict) else []),
    }
    (REP/"db_unify_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "written": str(REP/"db_unify_summary.json")}))

if __name__=="__main__": main()
