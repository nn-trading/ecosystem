# dev/update_session_tasks.py
import json, time
from pathlib import Path

p = Path('logs/tasks.json')
with p.open('r', encoding='ascii', errors='ignore') as f:
    data = json.load(f)


def upsert_task(lst, item):
    for i, t in enumerate(lst):
        if t.get('id') == item['id']:
            for k, v in item.items():
                if v is not None:
                    t[k] = v
            return
    lst.append(item)


ses = list(data.get('session_tasks', []))

# Session status updates
upsert_task(ses, {
    "id": "restart-or-run",
    "title": "Run or restart headless orchestrator in controlled mode and monitor logs",
    "status": "done",
    "notes": "Run complete; health/stderr clean; proofs emitted."
})
upsert_task(ses, {
    "id": "continue-pending",
    "title": "Proceed to CORE-03-Design and CORE-01-Design",
    "status": "done",
    "notes": "Design notes added for CORE-03 and CORE-01 (ASCII-only)."
})
upsert_task(ses, {
    "id": "fix-crash",
    "title": "Fix any crash seen in stderr/health",
    "status": "todo"
})
upsert_task(ses, {
    "id": "summarize-progress",
    "title": "Summarize progress and update task statuses",
    "status": "todo"
})

# Design notes (ASCII-only)
core03_notes = (
    "Scope:\n"
    "- LoggerDB observability: events, kv, rollups, health.\n"
    "- FTS triggers compat with legacy; LIKE fallback always available.\n"
    "- Snapshot runs to runs/<ts>/ with summary and index.\n\n"
    "Components:\n"
    "- SQLite schema: events(id, ts, topic, sender, text, meta_json); kv(key, value_json); rollups(period, start_ts, end_ts, data_json).\n"
    "- FTS: vtable events_fts(text) with triggers to mirror events.text; guarded by _ensure_fts_triggers_compat().\n"
    "- CLI: stats, recent, search (LIKE/FTS), snapshot-run.\n\n"
    "Flows:\n"
    "- main -> EventBus -> LoggerDB.write_event(); ToolsRegistry tracer writes tool events.\n"
    "- summarizer: periodic mem.rollup writing to rollups; health check writes headless_health.json.\n\n"
    "Plan:\n"
    "1) Ensure FTS init hardened and backfill when empty.\n"
    "2) Add snapshot-run to produce runs/<ts> with README.txt and index.json.\n"
    "3) CLI: loggerdb_cli stats/recent/search wired to LoggerDB.\n"
    "4) Tests: basic LIKE search and snapshot-run end-to-end."
)

core01_notes = (
    "Scope:\n"
    "- Detect user intent, propose plan, execute, and replan on feedback.\n"
    "- Define success criteria and stop conditions.\n\n"
    "Components:\n"
    "- Intent parser: extract goal and constraints from prompt/history.\n"
    "- Planner: build steps with tools and expectations.\n"
    "- Executor: run steps via ToolsRegistry; collect results in LoggerDB.\n"
    "- Evaluator: check success via assertions or heuristics; trigger replanning.\n\n"
    "Flows:\n"
    "- Inputs: current tasks.json, recent events, repo state.\n"
    "- Output: proposed task updates and actionable step list.\n\n"
    "Plan:\n"
    "1) Implement simple rule-based intent parser as baseline.\n"
    "2) Implement planner producing a linear step list with expected signals.\n"
    "3) Implement evaluator that checks for goal keywords/files/exit status.\n"
    "4) Add replan loop that adjusts remaining steps on failure."
)

upsert_task(ses, {
    "id": "CORE-03-Design",
    "title": "Design for logger/memory SQLite and summarizer",
    "status": "todo",
    "notes": core03_notes
})

upsert_task(ses, {
    "id": "CORE-01-Design",
    "title": "Design for intent detection and replanning",
    "status": "todo",
    "notes": core01_notes
})

# Persist
data['session_tasks'] = ses
data['updated_ts'] = int(time.time())
with p.open('w', encoding='ascii', errors='ignore') as f:
    json.dump(data, f, ensure_ascii=True, indent=2)
    f.write('\n')
print('updated logs/tasks.json')
