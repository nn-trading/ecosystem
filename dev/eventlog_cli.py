import argparse, os, sys, json, time
from pathlib import Path

# Local import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory.eventlog import EventLog  # type: ignore

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
    ev = EventLog()
    s = ev.stats()
    _write_json_ascii(Path(args.output) if args.output else Path("-"), s) if args.output else print(json.dumps(s, **ASCII_JSON_KW))
    return 0


def cmd_recent(args) -> int:
    ev = EventLog()
    rows = ev.recent(args.n)
    if args.output:
        _write_json_ascii(Path(args.output), rows)
    else:
        print(json.dumps(rows, **ASCII_JSON_KW))
    return 0


def cmd_search(args) -> int:
    ev = EventLog()
    rows = ev.search(args.query, args.n)
    if args.output:
        _write_json_ascii(Path(args.output), rows)
    else:
        print(json.dumps(rows, **ASCII_JSON_KW))
    return 0


def cmd_rollup(args) -> int:
    ev = EventLog()
    res = ev.rollup(args.keep)
    if args.output:
        _write_json_ascii(Path(args.output), res)
    else:
        print(json.dumps(res, **ASCII_JSON_KW))
    return 0


def cmd_db_path(args) -> int:
    ev = EventLog()
    info = {"db_path": str(ev.db_path)}
    if args.output:
        _write_json_ascii(Path(args.output), info)
    else:
        print(json.dumps(info, **ASCII_JSON_KW))
    return 0


def _top_topics(ev: EventLog, limit: int = 10):
    cur = ev.conn.execute(
        "SELECT topic, COUNT(*) AS c FROM events GROUP BY topic ORDER BY c DESC LIMIT ?",
        (limit,),
    )
    return [[r[0], int(r[1])] for r in cur.fetchall()]


def cmd_export_jsonl(args) -> int:
    ev = EventLog()
    n = args.n
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = ev.recent(n)
    with open(out, "w", encoding="ascii", errors="ignore") as f:
        for r in rows:
            f.write(json.dumps(r, **ASCII_JSON_KW))
            f.write("\n")
    return 0


def cmd_snapshot_run(args) -> int:
    ev = EventLog()
    ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    run_dir = Path("runs") / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    # Stats
    stats = ev.stats()
    _write_json_ascii(run_dir / "stats.json", stats)

    # Recent events
    rows = ev.recent(args.n)
    _write_json_ascii(run_dir / "recent.json", rows)

    # Top topics
    top = _top_topics(ev, 10)
    _write_json_ascii(run_dir / "top_topics.json", top)

    # Summary
    summary_lines = []
    summary_lines.append(f"Run snapshot: {ts}")
    summary_lines.append(f"Total events: {stats.get('total')}")
    summary_lines.append(f"Rollups: {stats.get('rollups')}")
    summary_lines.append("Top topics:")
    for t, c in top:
        summary_lines.append(f"- {t}: {c}")
    summary_txt = "\n".join(summary_lines)
    _write_text_ascii(run_dir / "summary.txt", summary_txt)

    # README and index for consumers
    readme_lines = []
    readme_lines.append("Ecosystem AI run snapshot (ASCII-only)")
    readme_lines.append("")
    readme_lines.append(f"Directory: runs/{ts}")
    readme_lines.append(f"Total events: {stats.get('total')}")
    readme_lines.append("Artifacts:")
    readme_lines.append("- stats.json: DB stats")
    readme_lines.append("- recent.json: recent events (chronological)")
    readme_lines.append("- top_topics.json: [topic, count] pairs")
    readme_lines.append("- summary.txt: human-readable summary")
    _write_text_ascii(run_dir / "README.txt", "\n".join(readme_lines))

    index = {
        "ts": ts,
        "dir": f"runs/{ts}",
        "stats_path": f"runs/{ts}/stats.json",
        "recent_path": f"runs/{ts}/recent.json",
        "top_topics_path": f"runs/{ts}/top_topics.json",
        "summary_path": f"runs/{ts}/summary.txt",
        "readme_path": f"runs/{ts}/README.txt",
    }
    _write_json_ascii(run_dir / "index.json", index)

    print(str(run_dir))
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="EventLog CLI")
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

    sp = sub.add_parser("rollup", help="Summarize and prune old events")
    sp.add_argument("-k", "--keep", type=int, default=500_000, help="Max rows to keep")
    sp.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    sp.set_defaults(func=cmd_rollup)

    sp = sub.add_parser("export-jsonl", help="Export recent events as JSONL")
    sp.add_argument("-n", type=int, default=1000, help="Rows to export")
    sp.add_argument("-o", "--output", required=True, help="Output path (JSONL)")
    sp.set_defaults(func=cmd_export_jsonl)

    sp = sub.add_parser("db-path", help="Print resolved DB path")
    sp.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    sp.set_defaults(func=cmd_db_path)

    sp = sub.add_parser("snapshot-run", help="Write snapshot under runs/<ts>/")
    sp.add_argument("-n", type=int, default=200, help="Recent events to include")
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
