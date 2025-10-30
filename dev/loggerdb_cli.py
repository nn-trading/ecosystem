import argparse, json, sys, os, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory.logger_db import LoggerDB  # type: ignore

ASCII_JSON_KW = dict(ensure_ascii=True, separators=(",", ":"))


def _write_json_ascii(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", errors="ignore") as f:
        json.dump(data, f, **ASCII_JSON_KW)
        f.write("\n")


def _write_text_ascii(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", errors="ignore") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def cmd_stats(args) -> int:
    db = LoggerDB()
    s = db.stats()
    if args.output:
        _write_json_ascii(Path(args.output), s)
    else:
        print(json.dumps(s, **ASCII_JSON_KW))
    return 0


def cmd_recent(args) -> int:
    db = LoggerDB()
    rows = db.recent_events(args.n)
    if args.output:
        _write_json_ascii(Path(args.output), rows)
    else:
        print(json.dumps(rows, **ASCII_JSON_KW))
    return 0


def cmd_search(args) -> int:
    db = LoggerDB()
    rows = db.retrieve(args.query, k=args.n)
    if args.output:
        _write_json_ascii(Path(args.output), rows)
    else:
        print(json.dumps(rows, **ASCII_JSON_KW))
    return 0


def cmd_artifacts(args) -> int:
    db = LoggerDB()
    rows = db.recent_artifacts(args.n)
    if args.output:
        _write_json_ascii(Path(args.output), rows)
    else:
        print(json.dumps(rows, **ASCII_JSON_KW))
    return 0


def cmd_snapshot_run(args) -> int:
    db = LoggerDB()
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    run_dir = Path("runs") / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_json_ascii(run_dir / "stats.json", db.stats())
    _write_json_ascii(run_dir / "recent_events.json", db.recent_events(args.n))
    _write_json_ascii(run_dir / "artifacts.json", db.recent_artifacts(args.n))
    top = db.top_event_types(10)
    _write_json_ascii(run_dir / "top_event_types.json", top)

    lines = []
    lines.append(f"LoggerDB snapshot: {ts}")
    s = db.stats()
    lines.append(f"Events: {s.get('events')} artifacts: {s.get('artifacts')} skills: {s.get('skills')} memories: {s.get('memories')}")
    lines.append("Top event types:")
    for t, c in top:
        lines.append(f"- {t}: {c}")
    _write_text_ascii(run_dir / "summary.txt", "\n".join(lines))

    print(str(run_dir))
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="LoggerDB CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("stats", help="Show DB stats")
    sp.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("recent", help="Show recent events")
    sp.add_argument("-n", type=int, default=200, help="Number of events")
    sp.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    sp.set_defaults(func=cmd_recent)

    sp = sub.add_parser("search", help="Search events (FTS or LIKE)")
    sp.add_argument("query", help="Search query")
    sp.add_argument("-n", type=int, default=100, help="Max rows")
    sp.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("artifacts", help="Show recent artifacts")
    sp.add_argument("-n", type=int, default=200, help="Number of artifacts")
    sp.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    sp.set_defaults(func=cmd_artifacts)

    sp = sub.add_parser("snapshot-run", help="Write snapshot under runs/<ts>/")
    sp.add_argument("-n", type=int, default=200, help="Recent items to include")
    sp.set_defaults(func=cmd_snapshot_run)

    return p


def main(argv=None) -> int:
    try:
        p = build_parser()
        args = p.parse_args(argv)
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
