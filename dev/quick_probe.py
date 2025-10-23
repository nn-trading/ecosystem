import os, json, subprocess
root = os.path.abspath(os.path.join(os.path.dirname(file), '..'))
events = os.path.join(root, 'workspace', 'logs', 'events.jsonl')
n = int(os.environ.get('PROBE_TAIL','5'))

def tail_bytes(path, n, block_size=8*1024*1024):
    size = os.path.getsize(path) if os.path.exists(path) else 0
    if size == 0: return []
    blocks, nl, remaining = [], 0, size
    with open(path, 'rb') as f:
        while remaining > 0 and nl <= n:
            step = block_size if remaining >= block_size else remaining
            remaining -= step; f.seek(remaining)
            chunk = f.read(step); blocks.append(chunk); nl += chunk.count(b'\n')
    buf = b''.join(reversed(blocks))
    if buf.endswith(b'\n'): buf = buf[:-1]
    parts = buf.split(b'\n')
    if len(parts) > n: parts = parts[-n:]
    return parts

tail = tail_bytes(events, n)
hb = sum(b'"topic": "system/heartbeat"' in ln for ln in tail)
hl = sum(b'"topic": "system/health"' in ln for ln in tail)

pid_path = os.path.join(root, 'logs', 'headless_pid.txt')
alive = False
try:
    with open(pid_path, 'r', encoding='utf-8', errors='ignore') as f:
        pid = int((f.read() or '').strip().splitlines()[0].strip())
    rc = subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-Command', f'try {{ Get-Process -Id {pid} -ErrorAction Stop | Out-Null; exit 0 }} catch {{ exit 1 }}']).returncode
    alive = rc == 0
except Exception:
    pass

print(json.dumps({'tail_n': n, 'heartbeat_count': int(hb), 'health_count': int(hl), 'headless_pid_alive': alive}, ensure_ascii=False))
