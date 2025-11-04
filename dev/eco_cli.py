# dev/eco_cli.py
import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY   = str((ROOT/".venv/Scripts/python.exe").resolve())
EV   = ROOT/"dev/eventlog_cli.py"
DB   = ROOT/"dev/db_cli.py"
CO2  = ROOT/"dev/core02_planner.py"
CH   = ROOT/"dev/chatops_cli.py"

def run(args):
    return subprocess.run(args, capture_output=True, text=True)

def ensure(p: Path, name: str):
    if not p.exists():
        print(f'{{"ok":false,"error":"{name} not found","path":"{p}"}}')
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python dev\\eco_cli.py <ask \"text\" | apply | log-stats | log-recent [-n N] | log-search <term> [-n N] | log-tail [-n N] | db-health | db-stats | db-vacuum>")
        return
    cmd = sys.argv[1].lower()

    if cmd == "ask":
        ensure(CH, "chatops_cli")
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not text:
            print('{"ok":false,"error":"missing text"}'); return
        r = run([PY, str(CH), text]); print(r.stdout); return

    if cmd == "apply":
        ensure(CO2, "core02_planner")
        r = run([PY, str(CO2), "apply"]); print(r.stdout); return

    if cmd.startswith("log-"):
        ensure(EV, "eventlog_cli")
        if cmd == "log-stats":
            r = run([PY, str(EV), "stats"]); print(r.stdout); return
        if cmd == "log-recent":
            n = sys.argv[2] if len(sys.argv) > 2 else "25"
            r = run([PY, str(EV), "recent", "-n", n]); print(r.stdout); return
        if cmd == "log-search":
            if len(sys.argv) < 3:
                print('{"ok":false,"error":"missing search term"}'); return
            term = sys.argv[2]; n = sys.argv[3] if len(sys.argv) > 3 else "50"
            r = run([PY, str(EV), "search", term, "-n", n]); print(r.stdout); return
        if cmd == "log-tail":
            n = sys.argv[2] if len(sys.argv) > 2 else "200"
            r = run([PY, str(EV), "recent", "-n", n]); print(r.stdout); return

    if cmd.startswith("db-"):
        ensure(DB, "db_cli")
        if cmd == "db-health":
            r = run([PY, str(DB), "health"]); print(r.stdout); return
        if cmd == "db-stats":
            r = run([PY, str(DB), "stats"]); print(r.stdout); return
        if cmd == "db-vacuum":
            r = run([PY, str(DB), "vacuum"]); print(r.stdout); return

    print('{"ok":false,"error":"unknown command"}')

if __name__ == "__main__":
    main()
