import sqlite3, json
import os; db = os.environ.get('ECOSYS_MEMORY_DB', os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'var', 'events.db'))
con = sqlite3.connect(db)
cur = con.cursor()
def rows(sql, args=()):
    return [dict(id=r[0], topic=r[1], sender=r[2], payload_json=r[3]) for r in cur.execute(sql, args).fetchall()]

out = {
  "result_rows": rows("SELECT id,topic,sender,payload_json FROM events WHERE topic in ('task/result','test/passed') AND payload_json LIKE '%HELLO FROM RESUME%' ORDER BY id DESC LIMIT 10"),
  "any_hello": rows("SELECT id,topic,sender,substr(payload_json,1,200) FROM events WHERE payload_json LIKE '%HELLO FROM RESUME%' ORDER BY id DESC LIMIT 40"),
}
print(json.dumps(out, ensure_ascii=True))
con.close()
