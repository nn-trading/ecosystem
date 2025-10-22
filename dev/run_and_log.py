import os, sys, json, time, subprocess, shlex

# Ensure repo root on path without external env
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory import Memory
from memory.eventlog import EventLog


def main():
    if len(sys.argv) < 2:
        print("Usage: python dev/run_and_log.py <command parts...>", file=sys.stderr)
        sys.exit(2)

    cmd = " ".join(sys.argv[1:])
    cwd = os.getcwd()

    t0 = time.time()
    try:
        # Use shell=True for Windows command parsing; trust only local commands
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        rc = proc.returncode
        out = proc.stdout
        err = proc.stderr
    except Exception as e:
        rc = 999
        out = ""
        err = f"exception: {e}"
    dt = time.time() - t0

    # Truncate very large outputs to keep JSONL manageable
    def trunc(s, max_len=200000):
        if s is None:
            return ""
        if len(s) > max_len:
            return s[:max_len] + "\n...TRUNCATED..."
        return s

    payload = {
        "cmd": cmd,
        "cwd": cwd,
        "exit": rc,
        "duration_sec": round(dt, 6),
        "stdout": trunc(out),
        "stderr": trunc(err),
    }

    mem = Memory()
    # Log before printing to avoid output buffering issues
    import asyncio
    asyncio.run(mem.append_event("runner/exec", payload, sender="runner"))

    # Mirror to SQLite durable history as well
    try:
        elog = EventLog()
        elog.append("runner/exec", "runner", payload)
    except Exception:
        pass

    # Mirror command output to console
    if out:
        try:
            sys.stdout.write(out)
        except Exception:
            sys.stdout.write(out.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore"))
    if err:
        try:
            sys.stderr.write(err)
        except Exception:
            sys.stderr.write(err.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore"))

    sys.exit(rc)


if __name__ == "__main__":
    main()
