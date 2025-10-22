from __future__ import annotations
import platform, os, sys, datetime
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

def info() -> dict:
    return {
        "os": platform.platform(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "mem_total_gb": round(psutil.virtual_memory().total / (1024**3), 2) if psutil else None,
        "time": datetime.datetime.now().isoformat(),
        "cwd": os.getcwd(),
    }
