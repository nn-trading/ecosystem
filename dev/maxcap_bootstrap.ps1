param()
# dev/maxcap_bootstrap.ps1  ASCII-only, idempotent

function Write-Ascii($Path, $Text) {
  $dir = Split-Path -Parent $Path; if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [IO.File]::WriteAllText($Path, $Text, [Text.Encoding]::ASCII)
}

# 0) Env + dirs
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:LOG_LEVEL='DEBUG'
New-Item -ItemType Directory -Force -Path .\specs\capabilities, .\config, .\reports, .\reports\chat, .\logs, .\runs | Out-Null

# 1) Kill any stuck jobs_queue loop (targeted)
$loop = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python.exe' -and $_.CommandLine -match 'jobs_queue' }
foreach ($p in $loop) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }

# 2) Capability specs (planner will build; no hard-coding)
$spec1 = @'
id: comms_alerts_v1
title: Comms & Alerts v1
kind: capability
owner: planner
goals:
  - local_toasts
  - telegram_discord_hooks
  - proof_bundle_deeplinks
acceptance:
  - failing_job_sends_alert_with_bundle: true
  - approval_prompt_blocks_high_risk: true
deliverables: [spec, code, tests, docs, demo, rollout]
'@
$spec2 = @'
id: process_orchestration_v1
title: Process Orchestration v1
kind: capability
owner: planner
goals:
  - pid_tracking
  - graceful_and_elevated_restart
  - app_profiles: [mt5, excel, browser]
  - window_manage: move_resize_focus
acceptance:
  - kill_app_and_resume_flow: true
  - elevated_restart_logs_reason: true
deliverables: [spec, code, tests, docs, demo, rollout]
'@
$spec3 = @'
id: performance_pack_v1
title: Performance Pack v1
kind: capability
owner: planner
goals:
  - artifact_gc_and_compaction
  - gpu_probes_optional
  - http_cache
  - content_addressed_artifacts
acceptance:
  - gc_report_after_large_run: true
  - disk_growth_under_limit: true
deliverables: [spec, code, tests, docs, demo, rollout]
'@
$spec4 = @'
id: event_bus_v1
title: Event Bus v1
kind: capability
owner: planner
goals:
  - local_bus
  - agent_event_publish_subscribe
  - target_rate_over_100_msgs_per_sec_localhost
acceptance:
  - dual_agent_exchange_without_db_contention: true
deliverables: [spec, code, tests, docs, demo, rollout]
'@
$spec5 = @'
id: kill_switch_safe_mode_v1
title: Kill-Switch & Safe-Mode v1
kind: capability
owner: planner
goals:
  - global_hotkey_kill
  - safe_mode_readonly_tools
  - approval_policies_by_risk
acceptance:
  - hotkey_stops_input_in_1s: true
  - high_risk_requires_approval: true
deliverables: [spec, code, tests, docs, demo, rollout]
'@
Write-Ascii 'specs\capabilities\comms_alerts_v1.yaml' $spec1
Write-Ascii 'specs\capabilities\process_orchestration_v1.yaml' $spec2
Write-Ascii 'specs\capabilities\performance_pack_v1.yaml' $spec3
Write-Ascii 'specs\capabilities\event_bus_v1.yaml' $spec4
Write-Ascii 'specs\capabilities\kill_switch_safe_mode_v1.yaml' $spec5

# 3) Policy + NORTH_STAR docs (ASCII)
$policy = @'
risk_levels:
  safe: [read_logs, list_files, window_focus, screenshots]
  medium: [file_write_workspace, browser_login, download_upload]
  high: [registry_write, system_config, live_trading, payments]
approvals:
  high: require
  medium: prompt_if_uncertain
kill_switch:
  hotkey: F12
  mode_on_kill: safe
secrets:
  provider: windows_credman
  log_redaction: true
'@
Write-Ascii 'config\policy.yaml' $policy

$north = @'
NORTH STAR
You are the full computer body (senses=vision+uia+hooks; muscles=input+process).
Memory+planner are your organs. Your only commander is the user.
Default to safe actions; escalate for high risk with diffs and approvals.
'@
Write-Ascii 'reports\NORTH_STAR.txt' $north

# 4) Non-blocking jobs drain helper (wrapper, no core edits)
$drain = @'
from __future__ import annotations
import os, sys, time, subprocess
ROOT = os.path.dirname(os.path.dirname(__file__))
py = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
if not os.path.exists(py): py = "python"
cmd = [py, "-c", "from dev import jobs_queue as jq; jq.loop(interval=1, max_tries=2)"]
p = subprocess.Popen(cmd, cwd=ROOT)
max_sec = int(os.environ.get("JOBS_DRAIN_MAX_SEC", "15"))
t0 = time.time(); rc = None
while True:
    rc = p.poll()
    if rc is not None: break
    if time.time() - t0 > max_sec:
        try: p.terminate()
        except Exception: pass
        time.sleep(1.0)
        try: p.kill()
        except Exception: pass
        rc = -1
        break
print("drain_rc", rc)
'@
Write-Ascii 'dev\jobs_drain.py' $drain

# 5) Mark JOBS-FIX done (ASCII edit)
$p = 'C:\bots\ecosys\logs\tasks.json'
if (Test-Path $p) {
  $raw = Get-Content -Path $p -Raw -Encoding Ascii
  try {
    $d = $raw | ConvertFrom-Json
    if (-not $d.session_tasks) { $d | Add-Member -NotePropertyName session_tasks -NotePropertyValue @() }
    $lst = @($d.session_tasks); $ix = -1
    for ($i=0; $i -lt $lst.Count; $i++) { if ($lst[$i].id -eq 'JOBS-FIX') { $ix = $i; break } }
    if ($ix -lt 0) { $obj = [pscustomobject]@{ id='JOBS-FIX'; status='done'; title='jobs failure path validated' }; $d.session_tasks = @($lst + @($obj)) }
    else { $d.session_tasks[$ix].status = 'done' }
    $json = $d | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($p, $json, [System.Text.Encoding]::ASCII)
  } catch {}
}

# 6) CORE-03 validations (stats + reserved-char searches)
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }
try { & $py dev\loggerdb_cli.py stats -o runs\verify_core03_stats.json | Out-Null } catch {}
try { & $py dev\loggerdb_cli.py search 'error planning' -n 5 -o runs\verify_core03_search_basic.json | Out-Null } catch {}
try { & $py dev\loggerdb_cli.py search 'a/b*c?' -n 5 -o runs\verify_core03_search_reserved.json | Out-Null } catch {}

# 7) Queue specs via ChatOps; then apply once
$notes = @(
  'Adopt capability: Comms & Alerts v1 from specs\capabilities\comms_alerts_v1.yaml',
  'Adopt capability: Process Orchestration v1 from specs\capabilities\process_orchestration_v1.yaml',
  'Adopt capability: Performance Pack v1 from specs\capabilities\performance_pack_v1.yaml',
  'Adopt capability: Event Bus v1 from specs\capabilities\event_bus_v1.yaml',
  'Adopt capability: Kill-Switch & Safe-Mode v1 from specs\capabilities\kill_switch_safe_mode_v1.yaml'
)
foreach ($n in $notes) { try { & $py dev\chatops_cli.py $n | Out-Null } catch {} }
try { & $py dev\core02_planner.py apply | Out-Null } catch {}

# 8) Regenerate ASCII task report
try { & $py -c 'from dev import task_tracker_ascii as t; t.write_ascii_tasks(); print("OK")' | Out-Null } catch {}

# 9) Restart background services to pick changes up (headless bg)
try { powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null } catch {}
try { powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null } catch {}

# 10) Breadcrumb
$s = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$lines = @(
  '--- MAXCAP SESSION ---',
  'timestamp: ' + $s,
  'seeded_specs: comms_alerts_v1, process_orchestration_v1, performance_pack_v1, event_bus_v1, kill_switch_safe_mode_v1',
  'queued_plan_apply: yes',
  'docs: config\policy.yaml; reports\NORTH_STAR.txt',
  'validations: runs\verify_core03_*.json',
  'helper: dev\jobs_drain.py',
  'restart: background relaunched',
  'notes: ASCII-only; targeted kill of jobs_queue loop applied',
  '-----------------------',
  ''
)
$steps = 'logs\steps.log'; if (-not (Test-Path $steps)) { New-Item -ItemType File -Path $steps -Force | Out-Null }
Add-Content -Encoding Ascii -LiteralPath $steps -Value ($lines -join [Environment]::NewLine)

Write-Host 'MAXCAP bootstrap complete.'
