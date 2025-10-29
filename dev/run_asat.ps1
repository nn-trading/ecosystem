# dev/run_asat.ps1
# Purpose: Run acceptance test suite (pytest) with AGENT_DANGER_MODE=1 and capture ASCII-only audit artifacts.
# Usage: powershell -ExecutionPolicy Bypass -File dev\run_asat.ps1
# Output: runs\YYYYMMDD_HHMMSS\ (ASAT_Final_Audit.md, pytest_output.txt)
# Notes: UI macro test will open Notepad when AGENT_DANGER_MODE=1 on Windows.

$ErrorActionPreference = 'Stop'
$env:AGENT_DANGER_MODE = '1'

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$runDir = Join-Path -Path 'runs' -ChildPath $ts
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$pytestOut = Join-Path $runDir 'pytest_output.txt'
pytest -q --disable-warnings -rA 2>&1 | Tee-Object -FilePath $pytestOut

$summaryLine = (Get-Content $pytestOut | Select-String -Pattern 'passed|failed|skipped|warnings' | Select-Object -Last 1).ToString()

$auditPath = Join-Path $runDir 'ASAT_Final_Audit.md'
@(
  'ASAT Final Audit',
  '',
  ('Date: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')),
  ('Env: AGENT_DANGER_MODE=' + $env:AGENT_DANGER_MODE),
  ('Summary: ' + $summaryLine),
  '',
  ('Full pytest output: ' + $pytestOut)
) | Out-File -FilePath $auditPath -Encoding ascii

Write-Output ('ASAT_AUDIT_PATH=' + $auditPath)
