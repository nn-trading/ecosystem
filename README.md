Ecosystem AI

Overview
- Multi-agent ecosystem with event bus and SQLite-backed EventLog
- Headless or foreground modes, with numeric switch parameters for PowerShell
- Persistent logs and memory under var/ and logs/

Quick start (PowerShell)
- Stop any background instance
  powershell -NoProfile -File .\start.ps1 -Stop 1

- Start headless in background (ensures venv, deps)
  powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1

- Foreground finite run (12 seconds)
  powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 0 -StopAfterSec 12 -HeartbeatSec 1 -HealthSec 2

- Check EventLog
  python dev\eventlog_cli.py stats
  python dev\eventlog_cli.py recent -n 10
  python dev\eventlog_cli.py search "system/heartbeat" -n 5

Behavior
- main.py periodically writes system/heartbeat and system/health
- EventLog.search prefers FTS; on syntax error or empty hits with special characters, it retries with a quoted term, then falls back to LIKE on payload_json OR topic

Paths
- Database: var\events.db
- Override: set ECOSYS_MEMORY_DB to an absolute path to change the default
- Logs: logs\start_stdout.log, logs\start_stderr.log
- Snapshots: runs\YYYYMMDD-HHMMSS

Conventions
- ASCII-only output for logs and artifacts when possible
- Avoid hard-coded absolute paths; scripts resolve repo root at runtime

Examples
- Headless background with ensure-deps
  powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureDeps 1
- Foreground test run without pytest
  powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 0 -RunPytest 0 -StopAfterSec 8 -HeartbeatSec 1 -HealthSec 2
- Stop
  powershell -NoProfile -File .\start.ps1 -Stop 1


One-shot bring-up
- Run the orchestrator to stop background, ensure venv/deps, run a short headless smoke, run pytest, inventory files, and export artifacts:
  powershell -NoProfile -File .\dev\one_shot_bringup.ps1
- Artifacts will be placed under C:\bots\out, C:\bots\reports, and C:\bots\artifacts.
- Outputs are ASCII-only when possible and paths are resolved dynamically at runtime.

