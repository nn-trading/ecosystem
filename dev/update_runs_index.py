# Rebuild runs/index.json by scanning runs/* directories; ASCII-only output
import json, os
from pathlib import Path

ASCII_JSON_KW = dict(ensure_ascii=True, indent=2, separators=(",", ": "))


def load_json(path: Path):
    try:
        with open(path, "r", encoding="ascii", errors="ignore") as f:
            return json.load(f)
    except Exception:
        return None


def build_entry(d: Path):
    ts = d.name
    entry = {
        "ts": ts,
        "dir": str(d.resolve()),
        "total": None,
        "rollups": None,
        "fts": None,
        "top_topics": [],
    }
    stats = load_json(d / "stats.json")
    if isinstance(stats, dict) and "events" in stats:
        try:
            entry["total"] = int(stats.get("events"))
        except Exception:
            entry["total"] = None
    top = load_json(d / "top_topics.json")
    if not top:
        top = load_json(d / "top_event_types.json")
    if isinstance(top, list):
        # expect list of [topic, count]
        entry["top_topics"] = top
        entry["fts"] = True
    else:
        entry["fts"] = False
    return entry


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    runs = repo / "runs"
    runs.mkdir(exist_ok=True)
    entries = []
    for child in sorted(runs.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        if child.name.lower() == "index.json":
            continue
        entries.append(build_entry(child))
    out = {"runs": entries, "count": len(entries)}
    idx = runs / "index.json"
    with open(idx, "w", encoding="ascii", errors="ignore") as f:
        json.dump(out, f, **ASCII_JSON_KW)
        f.write("\n")
    print(f"wrote {idx} with {len(entries)} runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
