# Stop stray Ecosys main or doctor processes not tracked by start.ps1
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$ops = Join-Path $repo 'runs\current\ops_log.txt'
Add-Content -Encoding ASCII $ops ("STOP-STRAY begin " + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*\\main.py*' -or $_.CommandLine -like '*dev\\doctor.py*' }
if ($procs) {
  foreach ($p in $procs) {
    try {
      Add-Content -Encoding ASCII $ops ("[kill] PID {0}" -f $p.ProcessId)
      Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    } catch {}
  }
} else {
  Add-Content -Encoding ASCII $ops '[kill] none'
}
Add-Content -Encoding ASCII $ops ("STOP-STRAY end " + (Get-Date -Format 'yyyyMMdd-HHmmss'))
