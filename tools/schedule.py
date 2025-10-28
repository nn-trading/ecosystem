# C:\bots\ecosys\tools\schedule.py
from __future__ import annotations
import threading, time
from typing import Any, Dict, Callable, Optional

# Simple in-process scheduler (best-effort). Not persistent across process restarts.

_tasks = []  # list of (thread, name)


def _run_once(delay_s: float, fn: Callable[[], Dict[str, Any]], name: str) -> None:
    def _target():
        try:
            if delay_s > 0:
                time.sleep(delay_s)
            fn()
        except Exception:
            pass
    t = threading.Thread(target=_target, name=f"once:{name}", daemon=True)
    t.start()
    _tasks.append((t, name))


def _run_every(interval_s: float, fn: Callable[[], Dict[str, Any]], name: str, times: Optional[int]) -> None:
    def _target():
        n = 0
        while True:
            try:
                fn()
            except Exception:
                pass
            n += 1
            if times is not None and n >= times:
                break
            time.sleep(max(0.1, interval_s))
    t = threading.Thread(target=_target, name=f"every:{name}", daemon=True)
    t.start()
    _tasks.append((t, name))


def once(delay_s: float, name: str = "job", code: Optional[str] = None) -> Dict[str, Any]:
    def _noop() -> Dict[str, Any]:
        return {"ok": True, "event": name}
    _run_once(max(0.0, float(delay_s)), _noop, name)
    return {"ok": True, "scheduled": name, "delay_s": float(delay_s)}


def every(interval_s: float, name: str = "job", times: Optional[int] = None) -> Dict[str, Any]:
    def _noop() -> Dict[str, Any]:
        return {"ok": True, "event": name}
    _run_every(max(0.1, float(interval_s)), _noop, name, times if times is None else int(times))
    return {"ok": True, "scheduled": name, "interval_s": float(interval_s), "times": times}


def list_tasks() -> Dict[str, Any]:
    items = []
    for t, name in list(_tasks):
        items.append({"name": name, "alive": t.is_alive()})
    return {"ok": True, "count": len(items), "tasks": items}


def register(reg) -> None:
    reg.add("schedule.once", once, desc="Schedule a one-shot in-process task (best-effort)")
    reg.add("schedule.every", every, desc="Schedule a repeating in-process task (best-effort)")
    reg.add("schedule.list", list_tasks, desc="List scheduled tasks (in-process)")
