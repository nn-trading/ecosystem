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
