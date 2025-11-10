# Run Google Flights screenshot demo via brain_orchestrator
param([string]$GoalParam)
$ErrorActionPreference = 'Stop'
. C:\bots\ecosys\dev\use_gptoss.ps1
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$goal = $GoalParam
if (-not $goal) { $goal = 'Open Google Flights and take a screenshot to C:\bots\ecosys\reports\screens\flights.png' }
$py = $null
$pyCandidates = @('C:\bots\ecosys\.venv\Scripts\python.exe', 'py', 'python', 'python3')
foreach ($c in $pyCandidates) {
  try { $cmd = Get-Command $c -ErrorAction SilentlyContinue } catch { $cmd = $null }
  if ($cmd) { $py = $cmd.Path; break }
}
if (-not $py) { $py = 'python' }
& $py C:\bots\ecosys\brain_orchestrator.py --goal "$goal" --max_iters 3
