import os, sys, json, subprocess, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.memory import Memory

def tail_bytes(path, n, block_size=8*1024*1024):
    if not os.path.exists(path): return []
    size = os.path.getsize(path)
    if size == 0: return []
    blocks, nl, remaining = [], 0, size
    with open(path, "rb") as f:
        while remaining > 0 and nl <= n:
            step = block_size if remaining >= block_size else remaining
            remaining -= step; f.seek(remaining)
            chunk = f.read(step); blocks.append(chunk); nl += chunk.count(b"\n")
    buf = b"".join(reversed(blocks))
    if buf.endswith(b"\n"): buf = buf[:-1]
    parts = buf.split(b"\n")
    if len(parts) > n: parts = parts[-n:]
    return parts

def check_headless_alive(pid_path: str) -> bool:
    try:
        with open(pid_path, "r", encoding="utf-8", errors="ignore") as f:
            pid = int((f.read() or "").strip().splitlines()[0].strip())
    except Exception:
        return False
    try:
        rc = subprocess.run([
            "powershell","-NoProfile","-ExecutionPolicy","Bypass",
            "-Command", f"try {{ Get-Process -Id {pid} -ErrorAction Stop | Out-Null; exit 0 }} catch {{ exit 1 }}"
        ]).returncode
        return rc == 0
    except Exception:
        return False

def main():
    n = int(os.environ.get("PROBE_TAIL", "500"))
    mem = Memory()
    events_path = mem.events_path
    tail = tail_bytes(events_path, n)

    hb_count = 0
    hl_count = 0
    hb_tail = []
    hl_tail = []
    for raw in tail:
        try:
            s = raw.decode("utf-8", errors="ignore")
            obj = json.loads(s)
            t = obj.get("topic")
            if t == "system/heartbeat":
                hb_count += 1; hb_tail.append(obj)
            elif t == "system/health":
                hl_count += 1; hl_tail.append(obj)
        except Exception:
            # skip malformed lines
            pass
    hb_tail = hb_tail[-3:]
    hl_tail = hl_tail[-3:]

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    pid_path = os.path.join(root, "logs", "headless_pid.txt")
    alive = check_headless_alive(pid_path) if os.path.exists(pid_path) else False

    out = {
        "tail_n": n,
        "heartbeat_count": hb_count,
        "health_count": hl_count,
        "heartbeat_tail": hb_tail,
        "health_tail": hl_tail,
        "headless_pid_alive": alive,
    }
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()


