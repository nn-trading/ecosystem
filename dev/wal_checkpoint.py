import sqlite3, pathlib
db = pathlib.Path("var/events.db")
if db.exists():
    con = sqlite3.connect(db, timeout=8)
    cur = con.cursor()
    cur.execute("PRAGMA wal_checkpoint(FULL)")
    cur.execute("PRAGMA optimize")
    con.commit(); con.close()
print("OK")