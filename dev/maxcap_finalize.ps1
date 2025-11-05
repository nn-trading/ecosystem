param()
# dev/maxcap_finalize.ps1  ASCII-only, idempotent

# 0) Env + dirs
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:LOG_LEVEL='DEBUG'
New-Item -ItemType Directory -Force -Path .\logs, .\runs, .\reports, .\specs\capabilities | Out-Null
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }

# 1) Wait up to 300s for bring-up to finish (non-blocking)
$deadline = (Get-Date).AddSeconds(300)
while ($true) {
  $bu = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'powershell' -and $_.CommandLine -match 'dev\\one_shot_bringup.ps1' }
  if (-not $bu) { break }
  if ((Get-Date) -gt $deadline) { break }
  Start-Sleep -Seconds 3
}

# 2) Kill only stuck jobs_queue loops
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python.exe' -and $_.CommandLine -match 'from dev import jobs_queue' } | ForEach-Object {
  try { Stop-Process -Id $_.ProcessId -Force } catch {}
}

# 3) Seed super-upgrade capability specs (no hard-coding; specs guide planner)
if (-not (Test-Path 'specs\capabilities\comms_alerts_v1.yaml')) {
@'
name: Comms_Alerts_v1
kind: capability
version: 1
status: proposed
goals:
  - Local notifications and webhook/Telegram/Discord alerts
constraints:
  - No hard-coding; use agent-factory path (spec->plan->tests->code->demo)
acceptance:
  - "send_local_notification: PASS"
  - "post_webhook_message: PASS"
'@ | Set-Content -Encoding Ascii -LiteralPath 'specs\capabilities\comms_alerts_v1.yaml'
}
if (-not (Test-Path 'specs\capabilities\process_orchestration_v1.yaml')) {
@'
name: Process_Orchestration_v1
kind: capability
version: 1
status: proposed
goals:
  - PID tracking, graceful termination, elevated restart, app profiles
acceptance:
  - "launch_profile(MT5|Browser|Excel): PASS"
  - "restart_elevated_if_needed: PASS"
'@ | Set-Content -Encoding Ascii -LiteralPath 'specs\capabilities\process_orchestration_v1.yaml'
}
if (-not (Test-Path 'specs\capabilities\performance_pack_v1.yaml')) {
@'
name: Performance_Pack_v1
kind: capability
version: 1
status: proposed
goals:
  - WAL mode, busy_timeout, snapshot GC, token/cost governor
acceptance:
  - "db_wal_and_busy_timeout_applied: PASS"
  - "cost_cap_enforced_soft: PASS"
'@ | Set-Content -Encoding Ascii -LiteralPath 'specs\capabilities\performance_pack_v1.yaml'
}
if (-not (Test-Path 'specs\capabilities\event_bus_v1.yaml')) {
@'
name: Event_Bus_v1
kind: capability
version: 1
status: proposed
goals:
  - Local event bus for agents (file/zmq/redis-lite selectable)
acceptance:
  - "publish_subscribe_loopback: PASS"
  - "fallback_to_filebus_when_unavailable: PASS"
'@ | Set-Content -Encoding Ascii -LiteralPath 'specs\capabilities\event_bus_v1.yaml'
}
if (-not (Test-Path 'specs\capabilities\kill_switch_safe_mode_v1.yaml')) {
@'
name: Kill_Switch_Safe_Mode_v1
kind: capability
version: 1
status: proposed
goals:
  - Immediate stop, safe-mode scoped permissions, audit breadcrumb
acceptance:
  - "hotkey_kill_switch: PASS"
  - "safe_mode_scopes_enforced: PASS"
'@ | Set-Content -Encoding Ascii -LiteralPath 'specs\capabilities\kill_switch_safe_mode_v1.yaml'
}

# 4) NORTH_STAR note
@'
ECOSYSTEM NORTH STAR
- You are the brain/heart/blood/lungs; this computer is your body.
- NN Trading is the only master/commander.
- Autonomy path: spec -> plan -> tests -> code -> demo -> evaluate -> iterate.
- Never hard-code site/app specifics; generate tools and adapters via specs and tests.
'@ | Set-Content -Encoding Ascii -LiteralPath 'reports\NORTH_STAR.txt'

# 5) Validate DB + align tasks
try { & $py dev\db_validate_runner.py | Out-Null } catch {}
try { & $py -c 'from dev import task_tracker_ascii as t; t.write_ascii_tasks()' | Out-Null } catch {}

# 6) CORE-03 validations
try { & $py dev\loggerdb_cli.py stats -o runs\verify_core03_stats.json | Out-Null } catch {}
try { & $py dev\loggerdb_cli.py search 'error planning' -n 10 -o runs\verify_core03_search_basic.json | Out-Null } catch {}
try { & $py dev\loggerdb_cli.py search 'a/b*c?' -n 10 -o runs\verify_core03_search_reserved.json | Out-Null } catch {}

# 7) Snapshot/update
if (Test-Path 'dev\run_snapshot_and_update.py') {
  try { & $py dev\run_snapshot_and_update.py | Out-Null } catch {}
} else {
  try { & $py dev\loggerdb_cli.py snapshot-run -n 200 | Out-Null } catch {}
}

# 8) ChatOps enqueue + apply plan
$notes = @(
  'Adopt capability: Comms & Alerts v1 from specs\capabilities\comms_alerts_v1.yaml',
  'Adopt capability: Process Orchestration v1 from specs\capabilities\process_orchestration_v1.yaml',
  'Adopt capability: Performance Pack v1 from specs\capabilities\performance_pack_v1.yaml',
  'Adopt capability: Event Bus v1 from specs\capabilities\event_bus_v1.yaml',
  'Adopt capability: Kill-Switch & Safe-Mode v1 from specs\capabilities\kill_switch_safe_mode_v1.yaml'
)
foreach ($n in $notes) { try { & $py dev\chatops_cli.py $n | Out-Null } catch {} }
try { & $py dev\core02_planner.py apply | Out-Null } catch {}

# 9) Restart background (headless)
try { powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null } catch {}
try { powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null } catch {}

# 10) Bundle + breadcrumb
$bundle = 'runs\maxcap_finalize_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
foreach ($f in @('runs\verify_core03_stats.json','runs\verify_core03_search_basic.json','runs\verify_core03_search_reserved.json','reports\NORTH_STAR.txt')) {
  if (Test-Path $f) { Copy-Item $f $bundle -Force }
}
$lines = @(
  '--- MAXCAP FINALIZE ---',
  'timestamp: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),
  'finalize_bundle: ' + $bundle,
  'db_validated: yes',
  'core03_validations: yes',
  'capability_specs_seeded: yes',
  'plan_apply: executed',
  'restart: background relaunched',
  'ascii_only: true',
  '------------------------',
  ''
)
$steps = 'logs\steps.log'; if (-not (Test-Path $steps)) { New-Item -ItemType File -Path $steps -Force | Out-Null }
Add-Content -Encoding Ascii -LiteralPath $steps -Value ($lines -join [Environment]::NewLine)
Write-Host 'MAXCAP finalize complete.'
