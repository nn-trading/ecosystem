import os, time, asyncio, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.memory import Memory

async def main():
    stop = int(os.environ.get("STOP_AFTER_SEC","12"))
    hb_sec = int(os.environ.get("HEARTBEAT_SEC","1"))
    hl_sec = int(os.environ.get("HEALTH_SEC","5"))
    mem = Memory()
    t0 = time.time()
    next_hb = t0
    next_hl = t0
    while time.time() - t0 < stop:
        now = time.time()
        if now >= next_hb:
            await mem.append_event("system/heartbeat", {"ts": now}, sender="headless")
            next_hb = now + hb_sec
        if now >= next_hl:
            await mem.append_event("system/health", {"ok": True}, sender="headless")
            next_hl = now + hl_sec
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())

