import os, json, re
from pathlib import Path
from typing import Dict, Any, List

ASCII_JSON_KW = dict(ensure_ascii=True, indent=2, separators=(",", ": "))


def read_json(path: Path) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json_ascii(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="ascii", errors="ignore") as f:
        json.dump(data, f, **ASCII_JSON_KW)
        f.write("\n")
    os.replace(tmp, path)


def summarize_runs(runs_dir: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"runs": []}
    if not runs_dir.exists():
        return out
    ts_re = re.compile(r"^\d{8}-\d{6}$")
    for child in sorted(runs_dir.iterdir()):
        if not child.is_dir() or not ts_re.match(child.name):
            continue
        stats = read_json(child / "stats.json") or {}
        top = read_json(child / "top_topics.json") or []
        entry = {
            "ts": child.name,
            "dir": str(child),
            "total": (stats or {}).get("total"),
            "rollups": (stats or {}).get("rollups"),
            "fts": (stats or {}).get("fts"),
            "top_topics": top,
        }
        out["runs"].append(entry)
    out["count"] = len(out["runs"])
    return out


def main() -> int:
    runs_dir = Path(__file__).resolve().parent.parent / "runs"
    summary = summarize_runs(runs_dir)
    write_json_ascii(runs_dir / "index.json", summary)
    print(str(runs_dir / "index.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
