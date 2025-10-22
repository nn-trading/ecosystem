import os, sys, json, asyncio

# Ensure repo root is on PYTHONPATH without relying on external env setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory import Memory


def main():
    # Usage:
    #   python dev/append_event.py <topic> <sender> [payload_json_or_text] [k=v ...]
    # Example:
    #   python dev/append_event.py runner/command openhands "{\"cmd\": \"git status\"}" step=pre
    args = sys.argv[1:]
    topic = args[0] if len(args) >= 1 else "runner/event"
    sender = args[1] if len(args) >= 2 else "runner"

    payload: dict = {}
    if len(args) >= 3:
        raw = args[2]
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"text": raw}

    # Allow k=v extra args to be merged into payload
    for a in args[3:]:
        if "=" in a:
            k, v = a.split("=", 1)
            payload[k] = v

    memory = Memory()
    asyncio.run(memory.append_event(topic, payload, sender=sender))


if __name__ == "__main__":
    main()
