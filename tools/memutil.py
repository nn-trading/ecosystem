# C:\bots\ecosys\tools\memutil.py
from __future__ import annotations

from typing import Dict, Any, List
from memory.eventlog import EventLog

def stats() -> Dict[str, Any]:
    log = EventLog()
    return {"ok": True, **log.stats()}

def rollup(max_keep: int = 500_000) -> Dict[str, Any]:
    log = EventLog()
    info = log.rollup(max_keep=max_keep)
    return {"ok": True, **info}

def search(query: str, limit: int = 100) -> Dict[str, Any]:
    log = EventLog()
    rows = log.search(query=query, limit=limit)
    # shrink payloads for display
    preview_rows: List[Dict[str, Any]] = []
    for r in rows:
        payload = r.get("payload", {})
        pv = str(payload)
        if len(pv) > 300:
            pv = pv[:300] + "..."
        preview_rows.append({
            "id": r["id"],
            "topic": r["topic"],
            "sender": r.get("sender"),
            "preview": pv,
        })
    return {"ok": True, "count": len(preview_rows), "rows": preview_rows}
