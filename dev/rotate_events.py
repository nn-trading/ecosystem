# dev/rotate_events.py
import os, sys, json, asyncio

# Ensure repo root on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory import Memory, DEFAULT_KEEP_LAST


def main():
    keep: int | None = None
    if len(sys.argv) > 1:
        try:
            keep = int(sys.argv[1])
        except Exception:
            keep = None
    if keep is None:
        try:
            keep = int(os.environ.get('KEEP_LAST', str(DEFAULT_KEEP_LAST)))
        except Exception:
            keep = DEFAULT_KEEP_LAST

    mem = Memory()

    async def run():
        old_count, new_count = await mem.rotate_keep_last(keep)
        payload = {
            'keep_last': keep,
            'old_count': old_count,
            'new_count': new_count,
            'events_file': mem.events_path,
        }
        await mem.append_event('memory/rotate', payload, sender='rotate_events')
        print(json.dumps({'ok': True, **payload}, ensure_ascii=True))

    asyncio.run(run())


if __name__ == '__main__':
    main()
