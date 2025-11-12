$ErrorActionPreference = "Stop"
$repo = "C:\bots\ecosys"
$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
Set-Location $repo
$log = Join-Path $repo "logs\mem_rollup.log"
$ts = Get-Date -Format s
try {
  $out = & $py "dev/mem_rollup.py" 2>&1
  "$ts $out" | Tee-Object -FilePath $log -Append | Out-Host
} catch {
  "$ts ERROR: $_" | Tee-Object -FilePath $log -Append | Out-Host
  exit 1
}
