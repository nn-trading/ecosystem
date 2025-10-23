# dev/fast_rotate.py
import os, sys, json, tempfile
from typing import List

# Ensure repo root on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory import Memory, DEFAULT_KEEP_LAST


def tail_last_lines(path: str, n: int, block_size: int = 8 * 1024 * 1024) -> List[str]:
    size = os.path.getsize(path)
    if size == 0:
        return []
    blocks = []
    nl = 0
    with open(path, 'rb') as f:
        remaining = size
        while remaining > 0 and nl <= n:
            step = block_size if remaining >= block_size else remaining
            remaining -= step
            f.seek(remaining)
            chunk = f.read(step)
            blocks.append(chunk)
            nl += chunk.count(b"\n")
    buf = b"".join(reversed(blocks))
    if buf.endswith(b"\n"):
        buf = buf[:-1]
    parts = buf.split(b"\n")
    if len(parts) > n:
        parts = parts[-n:]
    return [p.decode('utf-8', errors='ignore') for p in parts]


def main():
    keep = int(os.environ.get('KEEP_LAST', str(DEFAULT_KEEP_LAST)))
    mem = Memory()
    events = mem.events_path
    log_dir = os.path.dirname(events)

    # Read efficiently from the end
    tail_lines = tail_last_lines(events, keep)

    # Write to temporary and atomically replace
    fd, tmp_path = tempfile.mkstemp(prefix='events_tail_', suffix='.jsonl', dir=log_dir)
    os.close(fd)
    with open(tmp_path, 'w', encoding='utf-8') as w:
        for ln in tail_lines:
            w.write(ln if ln.endswith('\n') else ln + '\n')

    backup = events + '.bak'
    try:
        if os.path.exists(backup):
            os.remove(backup)
    except Exception:
        pass

    os.replace(events, backup)
    os.replace(tmp_path, events)
    try:
        os.remove(backup)
    except Exception:
        pass

    out = {
        'ok': True,
        'keep_last': keep,
        'new_count': len(tail_lines),
        'events_path': events,
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
