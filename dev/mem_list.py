import os, sqlite3, time
DB = r"C:\bots\ecosys\var\events.db"
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS summaries (id INTEGER PRIMARY KEY, ts REAL, span TEXT)")
cols = {r[1] for r in cur.execute("PRAGMA table_info(summaries)").fetchall()}
if 'text' not in cols:
    try:
        cur.execute("ALTER TABLE summaries ADD COLUMN text TEXT")
    except Exception:
        pass
rows = list(cur.execute("SELECT ts,span,length(text) FROM summaries ORDER BY rowid DESC LIMIT 3"))
print("SUMMARIES_TOP3:", rows)
