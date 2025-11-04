import sqlite3, json
p = r"C:\\bots\\ecosys\\var\\events.db"
con = sqlite3.connect(p)
cur = con.cursor()
res = {}
res['user_version'] = cur.execute('PRAGMA user_version').fetchone()[0]
row = cur.execute("SELECT value FROM meta WHERE key='fts_ready'").fetchone()
res['fts_ready'] = row[0] if row else None
res['index_list'] = cur.execute('PRAGMA index_list(events)').fetchall()
res['event_indexes'] = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='events'").fetchall()]
print(json.dumps(res))
