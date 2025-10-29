# dev/write_resume_marker.py
import os, sys, json, time, sqlite3

# Usage: python dev/write_resume_marker.py "message text"

def ensure_dirs(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass

def assistant_cfg_path():
    return os.environ.get("ASSISTANT_CONFIG_PATH", r"C:\\bots\\assistant\\config.json")

def load_cfg(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def write_assistant_jsonl(cfg: dict, message: str):
    log_dir = (
        os.environ.get("ASSISTANT_LOG_DIR")
        or os.environ.get("ECOSYS_ASSISTANT_LOG_DIR")
        or cfg.get("log_dir")
        or r"C:\\bots\\assistant\\logs"
    )
    ensure_dirs(log_dir)
    rec = {"ts": time.time(), "event": "resume_checkpoint", "text": message}
    p = os.path.join(log_dir, "assistant.jsonl")
    try:
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
    except Exception:
        pass


def write_sqlite_notes(cfg: dict, message: str):
    db = os.environ.get("ECOSYS_MEMORY_DB", cfg.get("memory_db") or r"C:\\bots\\data\\memory.db")
    ensure_dirs(os.path.dirname(db))
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, session_id TEXT, key TEXT, value TEXT)")
        cur.execute("INSERT OR REPLACE INTO kv(key,value) VALUES (?,?)", ("last_checkpoint", message))
        cur.execute("INSERT INTO notes(ts, session_id, key, value) VALUES (?,?,?,?)", (time.time(), cfg.get("last_session") or "", "checkpoint", message))
        con.commit(); con.close()
    except Exception:
        pass


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "manual_resume_marker"
    cfgp = assistant_cfg_path()
    ensure_dirs(os.path.dirname(cfgp))
    cfg = load_cfg(cfgp)
    write_assistant_jsonl(cfg, msg)
    write_sqlite_notes(cfg, msg)
    print(json.dumps({"ok": True, "msg": msg}, ensure_ascii=True))

if __name__ == "__main__":
    main()
