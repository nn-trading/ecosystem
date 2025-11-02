Ecosystem AI status (ASCII-only)

Location
- Repo: C:\bots\ecosys
- Branch: feature/loggerdb-cli

State
- EventLog: var\events.db (fts=true)
- start.ps1: numeric switches accepted (0/1) for Headless, Background, EnsureVenv, EnsureDeps, Stop, RunPytest
- Logs: logs\start_stdout.log and logs\start_stderr.log
- Bridge: main.py publishes system/heartbeat and system/health to EventLog via bridge

Usage examples (PowerShell)
- Stop background processes
  powershell -NoProfile -File .\start.ps1 -Stop 1

- Start headless in background, ensure deps
  powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureDeps 1

- Foreground run for 12 sec with fast heartbeats and health
  powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 0 -StopAfterSec 12 -HeartbeatSec 1 -HealthSec 2

- Run with pytest precheck disabled
  powershell -NoProfile -File .\start.ps1 -RunPytest 0

EventLog CLI
- Recent
  python dev\eventlog_cli.py recent -n 5
- Search (handles special chars with fallback)
  python dev\eventlog_cli.py search "ui/print" -n 3
- Stats
  python dev\eventlog_cli.py stats
- Snapshot run
  python dev\eventlog_cli.py snapshot-run -n 200

Notes
- All files written by tools prefer ASCII. JSON dumps use ensure_ascii=true.
- .gitignore excludes logs/, var/, runs/, workspace/logs/ artifacts, data/.

Entry points and dependency summary
Recent run: 20251102_102357
Pytest: 34 passed, 1 skipped, 3 warnings
Smoke: 60s background run completed; stdout captured to runs\current\smoke_60s.txt; summary no matches
Smoke-direct: 60s foreground run captured to runs\current\smoke_60s_direct.txt; summary no matches
Smoke-fg: attempt blocked by harness; use smoke_60s_direct.txt as substitute; re-run with longer timeout if needed

EventLog: snapshot at runs\20251102-134358 (stats/recent/top_topics); Total events: 63506; Top topic: system/heartbeat
Artifacts: runs\current\smoke_60s.txt, runs\current\smoke_60s_direct.txt, runs\current\eventlog_recent.json, ops_log updated
Next actions: CORE-01-Parser-Impl; CORE-03-Schema-Finalize; CORE-03-CLI-Converge; CORE-03-Search-Escapes; TASKS-align-core01; VCS hygiene; confirm remote; DOC-next-steps; STATUS-refresh; fix-crash

- Entry points: start.ps1, maintain.ps1, main.py
- EventLog CLI: dev\eventlog_cli.py (stats, recent, search, snapshot-run)
- Dependencies (from requirements.txt): rich, pydantic, psutil, prompt-toolkit, openai, pytest
- Virtual environment: .venv under repo root



Recent run: 20251101_132524
Pytest: 34 passed, 1 skipped, 0 warnings
Smoke: headless foreground run completed (StopAfterSec=10)
Artifacts: out, reports, artifacts under C:\bots
PR: refs/pull/1/head -> feature/loggerdb-cli (local bare remote)
PR summary: C:\bots\reports\PR_1.txt
Push summary: C:\bots\reports\bringup_push_summary.txt

