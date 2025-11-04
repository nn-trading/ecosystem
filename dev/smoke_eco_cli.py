# dev/smoke_eco_cli.py
from pathlib import Path
import subprocess, json

ROOT = Path(__file__).resolve().parents[1]
PY   = str((ROOT/".venv/Scripts/python.exe").resolve())
CLI  = ROOT/"dev/eco_cli.py"
LOGS = ROOT/"logs"; LOGS.mkdir(parents=True, exist_ok=True)
OUT  = LOGS/"smoke_eco_cli.out"

def run(args):
    return subprocess.run(args, capture_output=True, text=True)

parts = []
parts.append("= eco_cli log-stats =")
parts.append(run([PY, str(CLI), "log-stats"]).stdout)

parts.append("= eco_cli log-recent 5 =")
parts.append(run([PY, str(CLI), "log-recent", "5"]).stdout)

parts.append("= eco_cli log-search system/heartbeat 3 =")
parts.append(run([PY, str(CLI), "log-search", "system/heartbeat", "3"]).stdout)

parts.append("= eco_cli db-health =")
parts.append(run([PY, str(CLI), "db-health"]).stdout)

OUT.write_text("\n".join(parts), encoding="utf-8")
print(json.dumps({"ok": True, "out": str(OUT)}, ensure_ascii=True))
