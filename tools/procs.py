from __future__ import annotations
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

def top(limit: int = 20) -> dict:
    if not psutil:
        return {"ok": False, "error": "psutil not installed: pip install psutil"}
    out = []
    for p in psutil.process_iter(attrs=["pid","name","cpu_percent","memory_info"]):
        try:
            mi = p.info.get("memory_info")
            out.append({
                "pid": p.info.get("pid"),
                "name": p.info.get("name"),
                "cpu": p.info.get("cpu_percent"),
                "rss": getattr(mi, "rss", None)
            })
        except Exception:
            continue
    out = sorted(out, key=lambda x: (x.get("cpu") or 0), reverse=True)[:limit]
    return {"ok": True, "procs": out}

def kill(pid: int | None = None, name: str | None = None) -> dict:
    if not psutil:
        return {"ok": False, "error": "psutil not installed: pip install psutil"}
    try:
        if pid:
            p = psutil.Process(pid)
            p.terminate()
            return {"ok": True, "pid": pid}
        elif name:
            killed = []
            for p in psutil.process_iter(attrs=["pid","name"]):
                if p.info.get("name","").lower() == name.lower():
                    try:
                        p.terminate()
                        killed.append(p.info.get("pid"))
                    except Exception:
                        pass
            return {"ok": True, "name": name, "killed": killed}
        else:
            return {"ok": False, "error": "provide pid or name"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
