param()
$ErrorActionPreference='SilentlyContinue'
$ROOT = (Get-Item (Split-Path -Parent $MyInvocation.MyCommand.Path)).Parent.FullName
$REP  = Join-Path $ROOT 'reports'
$PIDS = Join-Path $REP  'AUTONOMOUS_PIDS.json'
try {
  if (Test-Path $PIDS) {
    $p = Get-Content -LiteralPath $PIDS | ConvertFrom-Json
    foreach($k in @('tool','dispatch','router')) {
      $pid = 0; try { $pid = [int]($p.$k) } catch {}
      if ($pid -gt 0) { try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {} }
    }
  }
} catch {}

$targets = @('dev.nl_router','dev.dispatcher','dev.brain_chat_shell','uvicorn','dev.tool_server:app')
try {
  Get-CimInstance Win32_Process | ForEach-Object {
    $n = $_.Name; $cmd = ($_.CommandLine | Out-String)
    $hit = $false
    foreach($t in $targets){ if ($cmd -like ("*"+$t+"*")) { $hit=$true; break } }
    if (($n -like 'python*.exe' -or $n -like 'py.exe') -and $hit) {
      try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
  }
} catch {}
