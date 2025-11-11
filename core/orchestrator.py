from __future__ import annotations
import argparse
import asyncio
import json
import os
from typing import Optional

from .bus import EventBus
from .events import UserRequest, PlanReady, WorkRequest, WorkResult, TestPassed, TestFailed, Done, LogEvent
from .llm_provider import load_provider
from .win_wait import wait_title_contains
from pathlib import Path
from memory.logger_db import get_logger_db

bus = EventBus()

async def comm_agent(headless: bool, smoke: bool):
    if smoke:
        await bus.publish("user/request", {"text": "Open Notepad, type ECOSYS OK, screenshot, close"}, sender="comm")

async def brain_agent():
    async for env in bus.subscribe("user/request"):
        text = env.payload.get("text", "")
        plan = f"SMOKE: {text}" if "Notepad" in text else f"Plan for: {text}"
        await bus.publish("plan/ready", {"plan": plan}, sender="brain", job_id=env.job_id)


def _safe_screenshot(default_path: Optional[str] = None) -> Optional[str]:
    try:
        import time
        import os
        import importlib
        mss = importlib.import_module("mss")
        Image = importlib.import_module("PIL.Image")
        path = default_path or os.path.join(r"C:\\bots\\ecosys\\reports\\screens", f"shot_{int(time.time())}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with mss.mss() as s:
            mon = 0
            mons = s.monitors
            if not mons:
                return None
            sshot = s.grab(mons[mon])
            img = Image.frombytes("RGB", sshot.size, sshot.bgra, "raw", "BGRX")
            img.save(path)
        return path
    except Exception:
        return None
    
async def worker_agent(headless: bool):
    async for env in bus.subscribe_prefix("plan/"):
        plan = env.payload.get("plan", "")
        if plan.startswith("SMOKE:"):
            try:
                # In headless mode or when explicitly stubbed via env, short-circuit fast
                if headless or (os.environ.get("ECOSYS_STUB_SMOKE", "").strip() not in ("", "0", "false", "False")):
                    await bus.publish("work/result", {"ok": True, "detail": "stubbed"}, sender="worker", job_id=env.job_id)
                    continue
                # Execute Notepad smoke (best-effort, may fail in headless CI)
                os.system("start notepad.exe")
                w = wait_title_contains("Notepad", timeout_sec=5)
                ok = bool(w.get("ok"))
                payload = {"ok": ok, "detail": json.dumps(w)}
                if ok:
                    # Optional screenshot
                    shot = _safe_screenshot()
                    if shot:
                        payload["screenshot"] = shot
                await bus.publish("work/result", payload, sender="worker", job_id=env.job_id)
            except Exception as e:
                await bus.publish("work/result", {"ok": False, "detail": str(e)}, sender="worker", job_id=env.job_id)
        else:
            await bus.publish("work/result", {"ok": True, "detail": "noop"}, sender="worker", job_id=env.job_id)

async def tester_agent():
    async for env in bus.subscribe("work/result"):
        if env.payload.get("ok"):
            await bus.publish("test/passed", {"name": "smoke"}, sender="tester", job_id=env.job_id)
        else:
            await bus.publish("test/failed", {"name": "smoke", "fix_brief": env.payload.get("detail", "")}, sender="tester", job_id=env.job_id)

async def logger_agent():
    db = get_logger_db()
    async for env in bus.subscribe_prefix(""):
        try:
            db.append_event(agent=env.src, type_=env.type, payload=env.payload)
            # If this message includes a screenshot path, capture as artifact
            if isinstance(env.payload, dict):
                p = env.payload.get("screenshot")
                if isinstance(p, str) and os.path.exists(p):
                    try:
                        db.add_artifact(Path(p))
                    except Exception:
                        pass
        except Exception:
            pass

async def finish_agent():
    async for env in bus.subscribe_prefix("test/"):
        # Publish done on either pass or fail to ensure smoke run terminates
        if env.type in ("test/passed", "test/failed"):
            status = "passed" if env.type == "test/passed" else "failed"
            await bus.publish("done", {"msg": f"smoke {status}"}, sender="orchestrator", job_id=env.job_id)
            break

async def run(headless: bool, smoke: bool):
    # Ensure we subscribe to 'done' before any agents can publish it
    done_event = asyncio.Event()

    async def _done_watcher():
        async for _ in bus.subscribe("done"):
            done_event.set()
            break

    asyncio.create_task(_done_watcher())

    # Start subscriber agents first so their subscriptions are registered
    tasks = [
        asyncio.create_task(brain_agent()),
        asyncio.create_task(worker_agent(headless)),
        asyncio.create_task(tester_agent()),
        asyncio.create_task(logger_agent()),
        asyncio.create_task(finish_agent()),
    ]
    # Let the event loop run once to register subscriptions
    await asyncio.sleep(0)

    if smoke:
        # Trigger the smoke request after subscribers are ready
        await comm_agent(headless, smoke)
        # Wait for Done event
        await done_event.wait()
        # Give tasks a brief chance to finish logging
        try:
            await asyncio.sleep(0)
        except Exception:
            pass
        return
    else:
        await asyncio.gather(*tasks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.headless, args.smoke))

if __name__ == "__main__":
    main()
