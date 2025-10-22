import os, sys, asyncio

# Ensure repo root is on PYTHONPATH without relying on external env setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory import Memory
from memory.eventlog import EventLog


def main():
    # Usage:
    #   python dev/log_text.py <role> [file_path]
    # If file_path is omitted, reads from STDIN.
    args = sys.argv[1:]
    if not args:
        print("Usage: python dev/log_text.py <role> [file_path]", file=sys.stderr)
        sys.exit(2)
    role = args[0]

    if len(args) >= 2:
        path = args[1]
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception as e:
            text = f"<read_error: {e}>"
    else:
        try:
            text = sys.stdin.read()
        except Exception as e:
            text = f"<stdin_error: {e}>"

    payload = {
        'role': role,
        'text': text,
        'chars': len(text or ''),
    }

    # Log to JSONL (hot log)
    mem = Memory()
    asyncio.run(mem.append_event('chat/message', payload, sender='assistant'))

    # Mirror to SQLite (durable)
    try:
        elog = EventLog()
        elog.append('chat/message', 'assistant', payload)
    except Exception:
        pass


if __name__ == '__main__':
    main()
