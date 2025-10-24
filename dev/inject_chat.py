# C:\bots\ecosys\dev\inject_chat.py
from __future__ import annotations
import sys, json, time
from memory.eventlog import EventLog

def main():
    if len(sys.argv) < 2:
        print("usage: inject_chat.py <text>")
        return 1
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print("empty text")
        return 1
    payload = {"role": "user", "text": text, "ts": time.time()}
    log = EventLog()
    try:
        log.append("chat/message", sender="inject", payload=payload)
        print(json.dumps({"ok": True, "text": text}))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{e.__class__.__name__}: {e}"}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
