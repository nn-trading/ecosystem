# C:\bots\ecosys\tools\sqliteutil.py
from __future__ import annotations
import os, sqlite3
from typing import Optional, Dict, Any, List, Tuple

def query(db_path: str, sql: str, max_rows: int = 10000) -> Dict[str, Any]:
    if not os.path.exists(db_path):
        return {"ok": False, "error": f"db not found: {db_path}"}
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute(sql)
        rows = cur.fetchmany(max_rows)
        cols = [d[0] for d in cur.description] if cur.description else []
        con.close()
        return {"ok": True, "columns": cols, "rows": rows}
    except Exception as e:
        return {"ok": False, "error": f"sqlite error: {e}"}

def execute(db_path: str, sql: str) -> Dict[str, Any]:
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.executescript(sql)
        con.commit()
        con.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"sqlite error: {e}"}
