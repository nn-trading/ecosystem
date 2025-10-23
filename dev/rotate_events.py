# dev/rotate_events.py
import os, sys, json, asyncio, tempfile

# Ensure repo root on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory import Memory, DEFAULT_KEEP_LAST


def main():
    keep = int(os.environ.get('KEEP_LAST', str(DEFAULT_KEEP_LAST)))
    mem = Memory()

    async def run():
        # Avoid full-file line counting on huge files; read tail only
        tail_lines = mem._tail_lines(mem.events_path, keep)
        # Write to temp and atomically replace
        log_dir = os.path.dirname(mem.events_path)
        fd, tmp_path = tempfile.mkstemp(prefix='events_', suffix='.jsonl', dir=log_dir)
        os.close(fd)
        with open(tmp_path, 'w', encoding='utf-8') as w:
            for ln in tail_lines:
                w.write(ln if ln.endswith('\n') else ln + '\n')
        # Backup then replace
        backup = mem.events_path + '.bak'
        try:
            if os.path.exists(backup):
                os.remove(backup)
        except Exception:
            pass
        os.replace(mem.events_path, backup)
        os.replace(tmp_path, mem.events_path)
        try:
            os.remove(backup)
        except Exception:
            pass
        payload = {
            'keep_last': keep,
            'new_count': len(tail_lines),
        }
        await mem.append_event('memory/rotate', payload, sender='rotate_events')
        print(json.dumps({'ok': True, **payload}, ensure_ascii=False))

    asyncio.run(run())


if __name__ == '__main__':
    main()
