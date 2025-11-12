Ecosystem AI

Overview
- Multi-agent ecosystem with event bus and SQLite-backed EventLog
- Headless or foreground modes, with numeric switch parameters for PowerShell
- Persistent logs and memory under var/ and logs/

One-click launch and smoke
- Run foreground smoke:
  powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 0
- The script prints exactly 4 lines:
  start.ps1: <absolute path>
  db: <ECOSYS_MEMORY_DB or var\events.db>
  screenshot: <latest reports\screens\shot_*.png or None>
  usage: .\start.ps1
- Stub smoke mode is enabled internally so the orchestrator runs without external dependencies.

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
  python dev\eventlog_cli.py search 'system/heartbeat' -n 5

Behavior
- main.py periodically writes system/heartbeat and system/health
- EventLog.search prefers FTS; on syntax error or empty hits with special characters, it retries with a quoted term, then falls back to LIKE on payload_json OR topic

Paths
- Database: var\events.db (overridden by ECOSYS_MEMORY_DB)
- Logs: logs\start_stdout.log, logs\start_stderr.log
- Screenshots: reports\screens
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

ToolForge and local tool development
- Create a spec in reports\inbox_tools, for example reports\inbox_tools\sample_calc.yaml:
  name: sample_calc
  entry: main
  description: sample tool skeleton
- Run: python dev\toolforge.py run
- ToolForge generates tools\<name>\<name>.py and <name>_cli.py, and updates tools\registry_local.json
- The spec is moved to reports\processed_tools with .done suffix after processing

Watcher flow
- start.ps1 launches the tools watcher (dev\core02_tools_watch.py) when Background=1
- The watcher monitors reports\inbox_tools and runs ToolForge for new specs
- Generated tools are auto-registered via tools\registry_local.json

Notes
- Numeric switches in PowerShell scripts accept 0/1 for booleans
- Logs are under logs\; pytest artifacts: logs\pytest_stdout.log, logs\pytest_stderr.log
- Known benign warning: on Python versions lacking ctypes.wintypes.LRESULT, tools.winui_pid defines a safe fallback and import continues
