import sqlite3
DB = r"C:\bots\ecosys\var\events.db"
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS summaries (id INTEGER PRIMARY KEY, ts REAL, span TEXT, text TEXT)")
cols = {r[1] for r in cur.execute("PRAGMA table_info(summaries)").fetchall()}
order_col = "id" if "id" in cols else ("ts" if "ts" in cols else "rowid")
rows = list(cur.execute(f"SELECT ts,span,length(text) FROM summaries ORDER BY {order_col} DESC LIMIT 3"))
print("SUMMARIES_TOP3:", rows)
