# dev/db_unify.py (ASCII-only)
from __future__ import annotations
import os, json, sqlite3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CFG  = ROOT/"config/db.yaml"
REP  = ROOT/"reports"


def _load_yaml(p:Path)->dict:
    try:
        import yaml
        return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}
    except Exception:
        return {}


def get_db_path()->str:
    cfg = _load_yaml(CFG)
    env_key = (cfg.get("memory_db_env") or "ECOSYS_MEMORY_DB").strip()
    p = os.environ.get(env_key)
    if p:
        return p
    default = cfg.get("default_memory_db") or "var\\events.db"
    return str((ROOT/default).resolve())


def health()->dict:
    path = get_db_path()
    ok = False; msg = None; one = None
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute((_load_yaml(CFG).get("health_query") or "SELECT 1;"))
        one = cur.fetchone()
        ok = True
    except Exception as e:
        msg = str(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass
    out = {"db_path": path, "ok": ok, "result": one, "msg": msg}
    (REP/"db_health.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def stats()->dict:
    import os
    p = get_db_path()
    size = os.path.getsize(p) if os.path.exists(p) else 0
    out = {"db_path": p, "exists": os.path.exists(p), "size_bytes": size}
    (REP/"db_stats.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def vacuum()->dict:
    p = get_db_path()
    before = 0
    try:
        import os
        before = os.path.getsize(p) if os.path.exists(p) else 0
        conn = sqlite3.connect(p)
        conn.execute("VACUUM;")
        conn.execute("PRAGMA optimize;")
        conn.close()
        after = os.path.getsize(p) if os.path.exists(p) else 0
        out = {"db_path": p, "ok": True, "before": before, "after": after}
    except Exception as e:
        out = {"db_path": p, "ok": False, "error": str(e), "before": before}
    (REP/"db_vacuum.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def snapshot()->dict:
    from datetime import datetime
    import shutil
    runs = ROOT/"runs"
    runs.mkdir(exist_ok=True)
    snap = runs/("db_unify_obs_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    snap.mkdir(exist_ok=True)
    copied = []
    missing = []
    for name in ("db_health.json","db_stats.json"):
        src = REP/name
        if src.exists():
            shutil.copy2(str(src), str(snap/src.name))
            copied.append(name)
        else:
            missing.append(name)
    out = {"snapshot": str(snap), "copied": copied, "missing": missing, "ok": True}
    (REP/"db_snapshot.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__=="__main__":
    import sys, json
    cmd = (sys.argv[1] if len(sys.argv)>1 else "health").lower()
    if cmd=="health":
        print(json.dumps(health(), indent=2))
    elif cmd=="stats":
        print(json.dumps(stats(), indent=2))
    elif cmd=="vacuum":
        print(json.dumps(vacuum(), indent=2))
    elif cmd=="snapshot":
        print(json.dumps(snapshot(), indent=2))
    else:
        print("Usage: python dev\\db_unify.py [health|stats|vacuum|snapshot]")
