# dev/core02_tools_watch.py (ASCII-only)
from __future__ import annotations
import time, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV  = ROOT/"dev"
AGENTS_DIR = ROOT/"agents/generated"
TOOLS_DIR  = ROOT/"tools/generated"

if str(DEV) not in sys.path:
    sys.path.append(str(DEV))
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def loop_once()->dict:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    # Import and run lightweight builders
    try:
        import agent_factory as af
        af.main()
    except Exception:
        pass
    try:
        import tools_builder as tb
        tb.main()
    except Exception:
        pass
    try:
        a_count = len(list(AGENTS_DIR.glob("*.txt")))
        t_count = len(list(TOOLS_DIR.glob("*.txt")))
    except Exception:
        a_count = t_count = 0
    # Emit a heartbeat into EventLog so watcher activity is visible
    try:
        from memory.eventlog import EventLog
        ev = EventLog()
        ev.append(
            topic="core/tools_watch",
            sender="core02_tools_watch",
            payload={"agents_txt": a_count, "tools_txt": t_count},
        )
    except Exception:
        pass
    return {"ok": True, "agents_txt": a_count, "tools_txt": t_count}


def main():
    import sys
    if len(sys.argv)>=2 and sys.argv[1]=="loop":
        while True:
            try:
                print(json.dumps(loop_once()))
            except Exception as e:
                print(json.dumps({"ok": False, "error": str(e)}))
            time.sleep(5)
    else:
        print(json.dumps(loop_once()))

if __name__=="__main__":
    main()
