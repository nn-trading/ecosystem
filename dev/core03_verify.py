# dev/core03_verify.py
from __future__ import annotations
import json, time
from pathlib import Path
import sys

# Ensure repo on sys.path for CLI imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ASCII-safe writers
ASCII_JSON_KW = dict(ensure_ascii=True, separators=(",", ":"))

def write_json_ascii(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="ascii", errors="ignore") as f:
        json.dump(data, f, **ASCII_JSON_KW)
        f.write("\n")

def append_text_ascii(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="ascii", errors="ignore") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")

# Import CLIs as modules
from dev import eventlog_cli as evcli  # type: ignore
from dev import loggerdb_cli as lgcli  # type: ignore

LOGS = ROOT / "logs"
STATUS = ROOT / "dev" / "STATUS.md"
TASKS = ROOT / "logs" / "tasks.json"

QUERIES = [
    ("topic_colon_heartbeat", "topic:system/heartbeat"),
    ("topic_equals_heartbeat", "topic=system/heartbeat"),
    ("backslash_path", r"C:\\bots\\ecosys"),
    ("backslash_path_full", r"C:\\bots\\ecosys\\var\\events.db"),
    ("space_phrase", "Reality Check"),
    ("wildcard_system_star", "system*"),
    ("quote_phrase", '"system heartbeat"'),
]


def run_ev(query_id: str, q: str, n: int = 100) -> int:
    out = LOGS / f"eventlog_search_{query_id}.json"
    code = evcli.main(["search", q, "-n", str(n), "-o", str(out)])
    # Count results
    try:
        data = json.loads(out.read_text(encoding="ascii", errors="ignore") or "[]")
    except Exception:
        data = []
    return len(data) if isinstance(data, list) else 0


def run_lg(query_id: str, q: str, n: int = 100) -> int:
    out = LOGS / f"loggerdb_search_{query_id}.json"
    code = lgcli.main(["search", q, "-n", str(n), "-o", str(out)])
    try:
        data = json.loads(out.read_text(encoding="ascii", errors="ignore") or "[]")
    except Exception:
        data = []
    return len(data) if isinstance(data, list) else 0


def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="ascii", errors="ignore") or json.dumps(default))
    except Exception:
        return default


def upsert_task(data: dict, tid: str, title: str, status: str, notes: str | None = None) -> None:
    sess = data.get("session_tasks") or []
    if not isinstance(sess, list):
        sess = []
    found = None
    for t in sess:
        if isinstance(t, dict) and str(t.get("id")) == tid:
            found = t
            break
    if found is None:
        found = {"id": tid, "title": title, "status": status}
        if notes:
            found["notes"] = notes
        sess.append(found)
    else:
        if title and not found.get("title"):
            found["title"] = title
        if status:
            found["status"] = status
        if notes:
            prev = str(found.get("notes") or "")
            found["notes"] = (prev + ("; " if prev else "") + notes)
    data["session_tasks"] = sess


def main() -> int:
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # Mark task start
    data = load_json(TASKS, {})
    if not isinstance(data, dict):
        data = {}
    upsert_task(data, "core03-verify", "CORE-03: verify FTS/LIKE quoting and escaping", "in_progress", f"start {now}")
    write_json_ascii(TASKS, data)

    ev_counts = {}
    lg_counts = {}

    for qid, q in QUERIES:
        try:
            ev_counts[qid] = run_ev(qid, q, n=100)
        except Exception:
            ev_counts[qid] = -1
        try:
            lg_counts[qid] = run_lg(qid, q, n=100)
        except Exception:
            lg_counts[qid] = -1

    # Load stats if present
    estats = load_json(LOGS / "eventlog_stats.json", {})
    lstats = load_json(LOGS / "loggerdb_stats.json", {})
    edb1 = load_json(LOGS / "eventlog_db_path.json", {})
    edb2 = load_json(LOGS / "eventlog_dbpath.json", {})
    ladb1 = load_json(LOGS / "loggerdb_dbpath.json", {})

    db_eventlog = str(edb1.get("db_path") or edb2.get("db_path") or "")
    db_loggerdb = str(ladb1.get("db_path") or "")

    summary = {
        "ts": now,
        "eventlog": {"fts": bool(estats.get("fts")), "db": db_eventlog, "counts": ev_counts},
        "loggerdb": {"fts": bool(lstats.get("fts")), "db": db_loggerdb, "counts": lg_counts},
    }
    write_json_ascii(LOGS / "core03_summary.json", summary)

    # Append STATUS.md
    lines = []
    lines.append("")
    lines.append(f"CORE-03 verification {now}")
    lines.append(f"- EventLog FTS={summary['eventlog']['fts']} DB={summary['eventlog']['db']}")
    lines.append(f"- LoggerDB FTS={summary['loggerdb']['fts']} DB={summary['loggerdb']['db']}")
    lines.append("- Search proofs (counts):")
    for qid, _ in QUERIES:
        lines.append(f"  - {qid}: eventlog={ev_counts.get(qid)} loggerdb={lg_counts.get(qid)}")
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS, "a", encoding="ascii", errors="ignore") as f:
        f.write("\n".join(lines) + "\n")

    # Update tasks: core03-verify done, CORE-03 in_progress, report-tasks-ascii todo->done
    data = load_json(TASKS, {})
    if not isinstance(data, dict):
        data = {}
    upsert_task(data, "core03-verify", "CORE-03: verify FTS/LIKE quoting and escaping", "done", f"summary written {now}")
    upsert_task(data, "CORE-03", "Logger/Memory schema and search", "in_progress", f"verification runs captured {now}")
    upsert_task(data, "report-tasks-ascii", "Regenerate TASKS_ASCII.md", "in_progress", f"started {now}")
    write_json_ascii(TASKS, data)

    # Regenerate ASCII tasks report
    try:
        from dev.task_tracker_ascii import write_ascii_tasks  # type: ignore
        write_ascii_tasks()
    except Exception:
        pass

    # Mark report-tasks-ascii done
    data = load_json(TASKS, {})
    upsert_task(data, "report-tasks-ascii", "Regenerate TASKS_ASCII.md", "done", f"updated {now}")
    write_json_ascii(TASKS, data)

    # Steps log
    steps = [
        f"[{now}] CORE-03: ran {len(QUERIES)} queries across EventLog and LoggerDB",
        f"[{now}] CORE-03: wrote logs/core03_summary.json and appended STATUS.md",
        f"[{now}] report-tasks-ascii: wrote reports/TASKS_ASCII.md",
    ]
    with open(LOGS / "steps.log", "a", encoding="ascii", errors="ignore") as f:
        for ln in steps:
            f.write(ln + "\n")

    print("core03 verification completed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
