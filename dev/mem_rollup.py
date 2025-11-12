import os, time, json, sqlite3
REPO = r"C:\bots\ecosys"
DB   = os.path.join(REPO, "var", "events.db")
os.makedirs(os.path.dirname(DB), exist_ok=True)
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS summaries (id INTEGER PRIMARY KEY, ts REAL, span TEXT, text TEXT)")
cols = {r[1] for r in cur.execute("PRAGMA table_info(events)").fetchall()}
want = ["ts","agent","topic","payload_json"]
sel = [c for c in want if c in cols]
if len(sel) < 3:
    sel = [c for c in ["ts","topic","payload_json"] if c in cols]
if not sel:
    print("MEM_SUMMARY_OK (no events yet)")
    raise SystemExit(0)
q = "SELECT " + ",".join(sel) + " FROM events ORDER BY id DESC LIMIT 500"
rows = cur.execute(q).fetchall()
lines=[]
for row in rows:
    rec = dict(zip(sel, row))
    ts   = rec.get("ts") or time.time()
    agent= rec.get("agent") or "-"
    topic= rec.get("topic") or "-"
    payload = rec.get("payload_json")
    line = f"[{ts:.0f}] {agent} {topic}"
    if payload:
        try:
            pj = json.loads(payload)
            brief = (pj.get("brief") or pj.get("msg") or pj.get("text") or "")
            if not isinstance(brief, str): brief = str(brief)
            line += " :: " + brief.strip().replace("\n"," ")[:160]
        except Exception:
            line += " :: " + str(payload).replace("\n"," ")[:160]
    lines.append(line)
blob = "\n".join(reversed(lines))[:2000]
cur.execute("INSERT INTO summaries(ts,span,text) VALUES(?,?,?)", (time.time(),"last_500", blob))
con.commit()
print("MEM_SUMMARY_OK")
