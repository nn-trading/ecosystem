Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
$ROOT = 'C:\bots\ecosys'
Set-Location -LiteralPath $ROOT

# --- Ensure minimal structure & configs ---
if (!(Test-Path -LiteralPath 'dev'))      { New-Item -ItemType Directory -Path 'dev'      | Out-Null }
if (!(Test-Path -LiteralPath 'configs'))  { New-Item -ItemType Directory -Path 'configs'  | Out-Null }
if (!(Test-Path -LiteralPath 'reports'))  { New-Item -ItemType Directory -Path 'reports'  | Out-Null }
if (!(Test-Path -LiteralPath 'reports\chat')) { New-Item -ItemType Directory -Path 'reports\chat' | Out-Null }

# Make dev a package so "-m dev.brain_chat_shell" works
if (!(Test-Path -LiteralPath 'dev\__init__.py')) { '' | Set-Content -Encoding Ascii -LiteralPath 'dev\__init__.py' }

# Hard-lock to GPT-5 and route comms to Brain with echo off
Set-Content -Encoding Ascii -LiteralPath 'configs\model.yaml' -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath 'configs\comms.yaml' -Value "mode: brain`necho: false`ntail: reports\chat\exact_tail.jsonl"

# --- Clean stop & cleanup of sticky state ---
try { powershell -NoProfile -File '.\start.ps1' -Stop 1 | Out-Null } catch {}
if (Test-Path -LiteralPath 'workspace\logs\events.jsonl') { Remove-Item -LiteralPath 'workspace\logs\events.jsonl' -Force -ErrorAction SilentlyContinue }
foreach ($f in @('var\events.db-wal','var\events.db-shm')) { if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue } }

# --- Start background headless, ensure venv & deps ---
powershell -NoProfile -File '.\start.ps1' -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null

# Ensure chat tail file exists
$tail = 'reports\chat\exact_tail.jsonl'
if (!(Test-Path -LiteralPath $tail)) { New-Item -ItemType File -Path $tail | Out-Null }

# --- Kick planner & send a trivial ask ---
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $py)) { $py = 'python' }

try { & $py 'dev\core02_planner.py' 'apply' | Out-Null } catch {}
try { & $py 'dev\eco_cli.py' 'ask' 'ping'  | Out-Null } catch {}

# --- Verify: find a real assistant/brain line (not "echo:") in the tail ---
$deadline = (Get-Date).AddSeconds(45)
$ok = $false
$lastText = ''
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Milliseconds 600
  $lines = $null
  try { $lines = Get-Content -Path $tail -Encoding UTF8 -Tail 300 } catch {}
  if ($null -eq $lines) { continue }
  for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    $ln = $lines[$i]
    try {
      $o = $ln | ConvertFrom-Json
      if ($o -and $o.role -and ($o.role -in @('assistant','brain')) -and $o.text -and ($o.text -notlike 'echo:*')) {
        $ok = $true; $lastText = [string]$o.text; break
      }
    } catch {}
  }
  if ($ok) { break }
}

# --- Write assert summary & (optionally) launch chat window ---
$summary = 'reports\FINAL_ASSERT.txt'
$ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
if ($ok) {
  Set-Content -Encoding Ascii -LiteralPath $summary -Value ("[$ts] OK: assistant reply observed -> " + ($lastText -replace "`r|`n"," " ).Trim())
  Write-Host 'OK - assistant reply observed in tail.'
} else {
  Set-Content -Encoding Ascii -LiteralPath $summary -Value "[$ts] FAIL: no assistant reply observed in tail within timeout."
  Write-Warning 'No assistant reply observed in tail within timeout.'
}

# Launch Brain Chat shell in its own window so it doesnt block this run
try {
  if (Test-Path -LiteralPath 'dev\brain_chat_shell.py') {
    Start-Process $py -ArgumentList '-m','dev.brain_chat_shell'
  } elseif (Test-Path -LiteralPath 'dev\chat_shell.py') {
    Start-Process $py -ArgumentList 'dev\chat_shell.py'
  } else {
    Write-Warning 'No chat shell found (dev\brain_chat_shell.py or dev\chat_shell.py missing). Background remains running.'
  }
} catch {}

# Also append a tiny breadcrumb
try {
  if (!(Test-Path -LiteralPath 'logs')) { New-Item -ItemType Directory -Path 'logs' | Out-Null }
  Add-Content -Encoding Ascii -LiteralPath 'logs\actions.log' -Value ("[$ts] oh_finalize ran: GPT-5 lock, comms->brain, background started, planner kicked, tail checked.")
} catch {}
