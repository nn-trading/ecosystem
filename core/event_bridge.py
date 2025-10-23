from __future__ import annotations
import asyncio
import json
from typing import Optional, List

from memory.eventlog import EventLog

META_KEY = "bridge.chat_last_id"

async def bridge_chat_to_bus(bus, poll_sec: float = 1.0) -> None:
    """
    Poll SQLite EventLog for new chat/message events and publish them to the bus.
    - Only processes rows with topic = 'chat/message'
    - Tracks last processed id in meta[bridge.chat_last_id] for exact resume
    - Routes role=='user' directly to 'task/new' so planning/execution proceeds
    """
    log = EventLog()
    cur = log.conn.cursor()

    def _get_last_id() -> int:
        try:
            row = cur.execute("SELECT value FROM meta WHERE key=?", (META_KEY,)).fetchone()
            if row and row[0]:
                return int(row[0])
        except Exception:
            pass
        try:
            row = cur.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE topic='chat/message'").fetchone()
            return int(row[0] or 0)
        except Exception:
            return 0

    def _set_last_id(v: int) -> None:
        try:
            log.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (META_KEY, str(int(v))))
            log.conn.commit()
        except Exception:
            pass

    last_id = _get_last_id()

    while True:
        try:
            rows = cur.execute(
                "SELECT id, payload_json FROM events WHERE topic='chat/message' AND id > ? ORDER BY id ASC LIMIT 100",
                (last_id,),
            ).fetchall()
            if not rows:
                await asyncio.sleep(poll_sec)
                continue

            for eid, pj in rows:
                role = None
                text = None
                try:
                    data = json.loads(pj) if pj else {}
                    role = (data.get("role") or "").strip().lower()
                    text = (data.get("text") or "").strip()
                except Exception:
                    text = None
                if text:
                    if role == "user":
                        await bus.publish("task/new", {"text": text}, sender="Bridge", job_id=f"chat.{eid}")
                    elif role == "assistant":
                        await bus.publish("ui/print", {"text": f"Assistant: {text}"}, sender="Bridge")
                last_id = eid
            _set_last_id(last_id)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(max(2.0, poll_sec))
async def bridge_topics_to_bus(bus, topics: List[str], poll_sec: float = 1.0, meta_prefix: str = "bridge") -> None:
    """
    Bridge selected topics from SQLite EventLog to the bus.
    - For each topic in `topics`, track last processed id in meta[f"{meta_prefix}.{topic}.last_id"].
    - Publish the payload as-is to the same topic on the bus.
    - On first run, default cursor to current max(id) for that topic to avoid replay flood.
    """
    log = EventLog()
    cur = log.conn.cursor()

    def _get_last_id(topic: str) -> int:
        key = f"{meta_prefix}.{topic}.last_id"
        try:
            row = cur.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            if row and row[0]:
                return int(row[0])
        except Exception:
            pass
        try:
            row = cur.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE topic=?", (topic,)).fetchone()
            return int(row[0] or 0)
        except Exception:
            return 0

    def _set_last_id(topic: str, v: int) -> None:
        key = f"{meta_prefix}.{topic}.last_id"
        try:
            log.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, str(int(v))))
            log.conn.commit()
        except Exception:
            pass

    last_ids = {t: _get_last_id(t) for t in topics}

    while True:
        try:
            progressed = False
            for topic in topics:
                last_id = last_ids.get(topic, 0)
                rows = cur.execute(
                    "SELECT id, sender, payload_json FROM events WHERE topic=? AND id > ? ORDER BY id ASC LIMIT 100",
                    (topic, last_id),
                ).fetchall()
                if not rows:
                    continue
                for eid, sender, pj in rows:
                    # Avoid feedback loops: skip events we originated or those from Main
                    if sender in ("Bridge", "Main"):
                        last_id = eid
                        continue
                    try:
                        data = json.loads(pj) if pj else None
                    except Exception:
                        data = None
                    await bus.publish(topic, data if isinstance(data, dict) else {}, sender="Bridge")
                    last_id = eid
                    progressed = True
                last_ids[topic] = last_id
                _set_last_id(topic, last_id)
            if not progressed:
                await asyncio.sleep(poll_sec)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(max(2.0, poll_sec))
