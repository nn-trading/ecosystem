# C:\bots\ecosys\dev\repo_search.py
from __future__ import annotations
import argparse, os, sys, json
from pathlib import Path

# Local import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.tools import REGISTRY as ToolsRegistry  # type: ignore

ASCII_JSON_KW = dict(ensure_ascii=True, separators=(",", ":"))

def _write_json_ascii(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", errors="ignore") as f:
        json.dump(data, f, **ASCII_JSON_KW)
        f.write("\n")


def cmd_search(args) -> int:
    root = args.root or str(Path(__file__).resolve().parent.parent)
    q = args.query
    res = ToolsRegistry.call(
        "repo.search",
        root=root,
        query=q,
        regex=bool(args.regex),
        icase=not args.case_sensitive,
        max_results=int(args.max)
    )
    if args.output:
        _write_json_ascii(Path(args.output), res)
    else:
        print(json.dumps(res, **ASCII_JSON_KW))
    return 0 if res.get("ok") else 2


def build_parser():
    p = argparse.ArgumentParser(description="Python-based repository search (ASCII-safe)")
    p.add_argument("query", help="Search query (literal by default; use --regex for patterns)")
    p.add_argument("--root", help="Root directory (default: repo root)")
    p.add_argument("--regex", action="store_true", help="Treat query as regex")
    p.add_argument("--case-sensitive", dest="case_sensitive", action="store_true", help="Case-sensitive search")
    p.add_argument("-m", "--max", type=int, default=1000, help="Max results")
    p.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    p.set_defaults(func=cmd_search)
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
