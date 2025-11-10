$ErrorActionPreference = "Stop"

# Load OpenRouter creds + env
$kpath = "C:\bots\ecosys\secrets\openrouter.key"
if(!(Test-Path $kpath)){ Write-Host "ERROR: missing $kpath" -ForegroundColor Red; Read-Host 'Press Enter to close'; exit 1 }
$env:OPENAI_API_BASE = "https://openrouter.ai/api/v1"
$env:OPENAI_API_KEY  = (Get-Content $kpath -Raw).Trim()
$env:OPENAI_MODEL    = "openai/gpt-oss-20b"
$env:PYTHONUTF8      = "1"
$env:PYTHONIOENCODING= "utf-8"

Write-Host "Ecosystem Front Chat  type a goal (or 'exit' to quit)." -ForegroundColor Cyan
while ($true) {
  $g = Read-Host -Prompt 'Goal'
  if ($null -eq $g) { continue }
  $t = $g.Trim()
  if ($t -eq '') { continue }
  if ($t.ToLower() -in @('exit','quit')) { break }
  try {
    & 'C:\bots\ecosys\dev\ecosys_goal.ps1' -Goal $t -Iters 3
  } catch {
    Write-Host ('Error: ' + $_.Exception.Message) -ForegroundColor Red
  }
}
