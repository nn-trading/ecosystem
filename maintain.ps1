param(
  [switch]$PurgeLogs = $true,
  [int]$KeepJsonLTail = 0, # 0 means delete events.jsonl instead of tailing (fast, recommended)
  [switch]$VacuumDbs = $true,
  [switch]$Restart = $true,
  [switch]$EnsureDeps = $false,
  [switch]$RunPytest = $false,
  [switch]$RunSnapshot = $false,
  [switch]$RunIndex = $false
)
$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

# Paths
$var = Join-Path $repo 'var'
$logs = Join-Path $repo 'logs'
$wslogs = Join-Path $repo 'workspace\logs'
$archive = Join-Path $var 'archives'
$maintDir = Join-Path $var 'maintenance'
New-Item -ItemType Directory -Force -Path $archive, $maintDir | Out-Null
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$logfile = Join-Path $maintDir ("maintain_" + $ts + ".log")

function Write-Log([string]$msg) {
  $line = "[{0}] {1}" -f ((Get-Date).ToString('o')), $msg
  $line | Tee-Object -FilePath $logfile -Append | Out-Host
}

function Remove-FileRobust([string]$path) {
  try {
    if (Test-Path $path) {
      Remove-Item -LiteralPath $path -Force -ErrorAction Stop
      Write-Log "Deleted $path"
      return $true
    }
  } catch { Write-Log "Delete failed for ${path}: $($_.Exception.Message)" }
  try {
    if (Test-Path $path) {
      $tmp = $path + '.deleting'
      try { Rename-Item -LiteralPath $path -NewName $tmp -ErrorAction Stop; $path = $tmp } catch { Write-Log "Rename failed for ${path}: $($_.Exception.Message)" }
    }
  } catch {}
  try {
    if (Test-Path $path) {
      $fs = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::ReadWrite)
      $fs.SetLength(0)
      $fs.Close()
      Write-Log "Truncated ${path} to 0 bytes"
      Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
      if (-not (Test-Path $path)) { Write-Log "Removed ${path} after truncate"; return $true }
    }
  } catch { Write-Log "Truncate failed for ${path}: $($_.Exception.Message)" }
  return -not (Test-Path $path)
}
function Schedule-DeleteOnReboot([string]$path) {
  try {
    $sig = @"
using System;
using System.Runtime.InteropServices;
public static class MoveFileExUtil {
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern bool MoveFileEx(string lpExistingFileName, string lpNewFileName, int dwFlags);
}
"@
    Add-Type -TypeDefinition $sig -ErrorAction SilentlyContinue | Out-Null
    $ok = [MoveFileExUtil]::MoveFileEx($path, $null, 4)
    if ($ok) { Write-Log "Scheduled delete on reboot: ${path}" } else { Write-Log "Failed to schedule delete on reboot: ${path} (Win32)" }
  } catch { Write-Log "Schedule-DeleteOnReboot error for ${path}: $($_.Exception.Message)" }
}

Write-Log "[BEGIN] repo=$repo"

# 1) Stop any background processes launched by start.ps1
try {
  Write-Log "Stopping background processes via start.ps1 -Stop"
  & (Join-Path $repo 'start.ps1') -Stop 1 | Tee-Object -FilePath $logfile -Append | Out-Host
} catch { Write-Log "start.ps1 -Stop threw: $($_.Exception.Message)" }

# Also kill stray python processes that point to this repo's main.py
try {
  $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -match 'python') -and ($_.CommandLine -match [regex]::Escape("$repo\\main.py"))
  }
  foreach ($p in $procs) {
    try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; Write-Log "Killed python PID $($p.ProcessId) cmd=$($p.CommandLine)" } catch { Write-Log "Failed to kill PID $($p.ProcessId): $($_.Exception.Message)" }
  }
} catch { Write-Log "Process sweep error: $($_.Exception.Message)" }

# 2) Manifest of workspace\logs before cleanup
try {
  if (Test-Path $wslogs) {
    $manifest = Join-Path $archive ("wslogs_manifest_" + $ts + ".txt")
    Get-ChildItem $wslogs -Recurse -File | Select-Object FullName,Length,LastWriteTime | Sort-Object Length -Descending | Format-Table -AutoSize | Out-String | Set-Content -Path $manifest -Encoding utf8
    $total = (Get-ChildItem $wslogs -Recurse -File | Measure-Object -Property Length -Sum).Sum
    Write-Log ("workspace\\logs total BEFORE: {0:N2} GB" -f ($total/1GB))
  } else {
    Write-Log "workspace\\logs does not exist; skipping manifest"
  }
} catch { Write-Log "Manifest error: $($_.Exception.Message)" }

# 3) Purge/rotate giant JSONL logs
if ($PurgeLogs -and (Test-Path $wslogs)) {
  try {
    $eventsJson = Join-Path $wslogs 'events.jsonl'
    $tails = @(Get-ChildItem $wslogs -Filter 'events_tail_*.jsonl' -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)

    if (Test-Path $eventsJson) {
      if ($KeepJsonLTail -gt 0) {
        Write-Log "Requested tail keep_last=$KeepJsonLTail, attempting fast tail may be slow on huge files"
        $tailOut = Join-Path $wslogs ("events.tail.last" + $KeepJsonLTail + ".jsonl")
        try {
          # Warning: Get-Content -Tail on extremely large files can be slow; do not block forever
          $job = Start-Job -ScriptBlock { param($f,$n,$out) Get-Content -Path $f -Tail $n -ReadCount 1000 | Set-Content -Path $out -Encoding utf8 } -ArgumentList $eventsJson,$KeepJsonLTail,$tailOut
          $ok = $job | Wait-Job -Timeout 300
          if (-not $ok) { Write-Log "Tail timed out after 300s; removing job and proceeding to deletion"; Stop-Job $job -ErrorAction SilentlyContinue; Remove-Job $job -Force -ErrorAction SilentlyContinue }
        } catch { Write-Log "Tail failed: $($_.Exception.Message)" }
      }
      try { Remove-Item -LiteralPath $eventsJson -Force -ErrorAction Stop; Write-Log "Deleted ${eventsJson}" } catch { Write-Log "Failed to delete ${eventsJson}: $($_.Exception.Message)" }
          if (Test-Path $eventsJson) {
            $ok = Remove-FileRobust -path $eventsJson
            if ($ok) {
              Write-Log "Deleted ${eventsJson} via robust path"
            } else {
              Write-Log "Still could not delete ${eventsJson}; scheduling delete on reboot"
              Schedule-DeleteOnReboot -path $eventsJson
            }
          }

    }

    foreach ($f in $tails) {
      try { Remove-Item -LiteralPath $f -Force -ErrorAction Stop; Write-Log "Deleted ${f}" } catch { Write-Log "Failed to delete ${f}: $($_.Exception.Message)" }
    }
  } catch { Write-Log "Purge error: $($_.Exception.Message)" }
}

# 4) Recalculate workspace\logs size
try {
  if (Test-Path $wslogs) {
    $after = (Get-ChildItem $wslogs -Recurse -File | Measure-Object -Property Length -Sum).Sum
    Write-Log ("workspace\\logs total AFTER: {0:N2} GB" -f ($after/1GB))
  }
} catch { Write-Log "Size recalc error: $($_.Exception.Message)" }


# 4b) Remove extremely large individual log files (>5 GB)
try {
  if (Test-Path $wslogs) {
    $threshold = 5GB
    $big = Get-ChildItem $wslogs -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt $threshold }
    foreach ($b in $big) {
      try {
        Remove-Item -LiteralPath $b.FullName -Force -ErrorAction Stop
        Write-Log ("Deleted large log {0} ({1:N2} GB)" -f $b.FullName, ($b.Length/1GB))
      } catch {
        Write-Log ("Failed to delete large log {0}: {1}" -f $b.FullName, $_.Exception.Message)
      }
    }
    $afterBig = (Get-ChildItem $wslogs -Recurse -File | Measure-Object -Property Length -Sum).Sum
    Write-Log ("workspace\\logs total AFTER large purge: {0:N2} GB" -f ($afterBig/1GB))
  }
} catch { Write-Log "Large purge error: $($_.Exception.Message)" }

# 5) Check and VACUUM SQLite DBs
if ($VacuumDbs) {
  try {
    $pyExe = Join-Path $repo '.venv/Scripts/python.exe'
    if (-not (Test-Path $pyExe)) {
      try { $pyExe = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1).Source } catch {}
      if (-not $pyExe) { $pyExe = 'python' }
    }

    $vacScript = @"
import sqlite3, os, sys
path = sys.argv[1]
try:
    con = sqlite3.connect(path)
    con.execute('PRAGMA journal_mode=DELETE')
    con.execute('VACUUM')
    con.close()
    print('[vacuum] OK', path)
except Exception as e:
    print('[vacuum] FAIL', path, e)
"@
    $vacPy = Join-Path $maintDir 'vacuum_sqlite.py'
    Set-Content -Path $vacPy -Value $vacScript -Encoding utf8

    # Prefer ECOSYS_MEMORY_DB if set; also check common legacy paths if they exist
    $dbs = @()
    if ($env:ECOSYS_MEMORY_DB) { $dbs += $env:ECOSYS_MEMORY_DB }
    $dbs += @((Join-Path $repo 'var\events.db'), 'C:\bots\data\memory.db', (Join-Path $repo 'data\ecosys.db'))
    $dbs = $dbs | Select-Object -Unique
    foreach ($db in $dbs) {
      if (Test-Path $db) {
        Write-Log "Vacuuming $db"
        & $pyExe $vacPy $db | Tee-Object -FilePath $logfile -Append | Out-Host
      } else { Write-Log "DB not found: $db" }
    }
  } catch { Write-Log "Vacuum error: $($_.Exception.Message)" }
}


# 5c) Optional LoggerDB snapshot and runs index
if ($RunSnapshot -or $RunIndex) {
  try {
    $pyExe = Join-Path $repo '.venv/Scripts/python.exe'
    if (-not (Test-Path $pyExe)) {
      try { $pyExe = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1).Source } catch {}
      if (-not $pyExe) { $pyExe = 'python' }
    }

    if ($RunSnapshot) {
      Write-Log "Running dev/loggerdb_cli.py snapshot-run"
      & $pyExe (Join-Path $repo 'dev/loggerdb_cli.py') 'snapshot-run' '-n' '200' 2>&1 | Tee-Object -FilePath $logfile -Append | Out-Host
    }
    if ($RunIndex) {
      Write-Log "Running dev/summarize_runs.py"
      & $pyExe (Join-Path $repo 'dev/summarize_runs.py') 2>&1 | Tee-Object -FilePath $logfile -Append | Out-Host
    }
  } catch { Write-Log "Snapshot/Index error: $($_.Exception.Message)" }
}


# 5b) Optional pytest run
if ($RunPytest) {
  try {
    $pyExe = Join-Path $repo '.venv/Scripts/python.exe'
    if (-not (Test-Path $pyExe)) {
      try { $pyExe = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1).Source } catch {}
      if (-not $pyExe) { $pyExe = 'python' }
    }
    Write-Log "Running pytest -q"
    & $pyExe -m pytest -q 2>&1 | Tee-Object -FilePath $logfile -Append | Out-Host
  } catch { Write-Log "pytest error: $($_.Exception.Message)" }
}

# 6) Optional restart
if ($Restart) {
  try {
    Write-Log "Starting environment headless/background"
    & (Join-Path $repo 'start.ps1') -Headless 1 -Background 1 -EnsureDeps $([int][bool]$EnsureDeps) | Tee-Object -FilePath $logfile -Append | Out-Host
    Start-Sleep -Seconds 5
    $stdout = Join-Path $logs 'start_stdout.log'
    if (Test-Path $stdout) {
      Write-Log "Last 100 lines of start_stdout.log:"
      Get-Content $stdout -Tail 100 | Tee-Object -FilePath $logfile -Append | Out-Host
    }
  } catch { Write-Log "Restart error: $($_.Exception.Message)" }
}

Write-Log "[END] maintenance complete"
