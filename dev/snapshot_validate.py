# ASCII-only snapshot validator
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)
OUT_JSON = REPORTS / "snapshot_validate.json"
ASCII_KW = dict(encoding="ascii", errors="ignore")

result = {"ok": True, "errors": [], "latest": None}
try:
    runs_dir = ROOT / "runs"
    indices = sorted(runs_dir.glob("*/index.json")) if runs_dir.exists() else []
    if not indices:
        result["ok"] = False
        result["errors"].append("no index.json found under runs/")
    else:
        latest = indices[-1]
        result["latest"] = str(latest)
        try:
            data = json.loads(latest.read_text(**ASCII_KW))
            keys = [
                "ts",
                "dir",
                "stats_path",
                "recent_path",
                "artifacts_path",
                "top_event_types_path",
                "summary_path",
                "readme_path",
            ]
            missing = [k for k in keys if k not in data]
            if missing:
                result["ok"] = False
                result["errors"].append("missing keys: " + ",".join(missing))
        except Exception:
            result["ok"] = False
            result["errors"].append("index parse error")
except Exception:
    result["ok"] = False
    result["errors"].append("exception")

with open(OUT_JSON, "w", **ASCII_KW) as f:
    json.dump(result, f, ensure_ascii=True, separators=(",", ":"))
    f.write("\n")
print(json.dumps(result, ensure_ascii=True))
