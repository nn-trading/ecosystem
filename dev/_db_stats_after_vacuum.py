import os, json, sqlite3, time
root = os.getcwd()
db = os.path.join(root, "var","events.db")
out = os.path.join(root, "runs","db_stats_after_vacuum.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
stat = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "db_path": db, "exists": os.path.exists(db)}
if stat["exists"]:
    try:
        stat["size_bytes"] = os.path.getsize(db)
    except Exception:
        stat["size_bytes"] = None
    try:
        con = sqlite3.connect(db)
        con.execute('PRAGMA busy_timeout=3000')
        cur = con.cursor()
        def safe_count(table):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                return cur.fetchone()[0]
            except Exception:
                return None
        stat["events"] = safe_count("events")
        stat["artifacts"] = safe_count("artifacts")
        try:
            cur.execute("PRAGMA journal_mode")
            stat["journal_mode"] = cur.fetchone()[0]
        except Exception:
            pass
        con.close()
    except Exception as e:
        stat["error"] = str(e)
with open(out, 'w', encoding='ascii', errors='ignore') as f:
    f.write(json.dumps(stat, ensure_ascii=True, indent=2))
print(out)
