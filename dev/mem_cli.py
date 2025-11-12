import sys, sqlite3, pathlib
DB = pathlib.Path("var/events.db")
q = " ".join(sys.argv[1:]) if len(sys.argv)>1 else ""
con = sqlite3.connect(DB); cur = con.cursor()
if q:
    for ts,agent,topic,pay in cur.execute("SELECT ts,agent,topic,payload_json FROM events WHERE payload_json LIKE ? ORDER BY ts DESC LIMIT 20", (f"%{q}%",)):
        print(ts, agent, topic)
else:
    for ts,span,summary in cur.execute("SELECT ts,span,summary FROM summaries ORDER BY ts DESC LIMIT 3"):
        print(ts, span, len(summary),"chars")
con.close()
