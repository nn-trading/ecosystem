Ecosystem AI status (ASCII-only)

Location
- Repo: C:\bots\ecosys
- Branch: feature/autonomy-core

State
- EventLog: var\events.db (fts=true). Override via ECOSYS_MEMORY_DB
- start.ps1: numeric switches accepted (0/1) for Headless, Background, EnsureVenv, EnsureDeps, Stop, RunPytest
- Logs: logs\start_stdout.log and logs\start_stderr.log
- Bridge: main.py publishes system/heartbeat and system/health to EventLog via bridge

One-click smoke output (expected)
- Run: powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 0
- Prints EXACTLY:
  start.ps1: <absolute path>
  db: <ECOSYS_MEMORY_DB or var\events.db>
  screenshot: <latest reports\screens\shot_*.png or None>
  usage: .\start.ps1

Recent
- Tests: previously green; artifacts at reports\tests
- Smoke: foreground run completed; screenshot path printed when available

Notes
- .gitignore excludes logs/, var/, runs/, workspace/logs/, artifacts/, out/, reports/tests/, __pycache__/, *.pyc, .venv/
- All files written by tools prefer ASCII. JSON dumps ensure_ascii=true.
