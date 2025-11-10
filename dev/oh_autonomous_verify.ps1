param()
$ErrorActionPreference='Stop'
$ROOT=(Get-Item (Split-Path -Parent $MyInvocation.MyCommand.Path)).Parent.FullName
$RT   = Join-Path $ROOT 'reports\chat\exact_tail.jsonl'
$SHDW = Join-Path $ROOT 'reports\chat\exact_tail_shadow.jsonl'
$EVT  = Join-Path $ROOT 'reports\DISPATCH_EVENTS.jsonl'
$OUT  = Join-Path $ROOT 'reports\AUTONOMOUS_VERIFY.txt'

function Add-UserLine([string]$text){
  $obj = [ordered]@{ ts = [int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); role = 'user'; text = $text }
  $json = ($obj | ConvertTo-Json -Compress)
  Add-Content -Encoding Ascii -LiteralPath $RT -Value $json
}

function Wait-Dispatch([int]$beforeCount, [int]$timeoutSec){
  $deadline=(Get-Date).AddSeconds($timeoutSec)
  while((Get-Date) -lt $deadline){
    $cnt = 0
    if(Test-Path $EVT){ $cnt=(Get-Content $EVT -ErrorAction SilentlyContinue | Measure-Object -Line).Lines }
    if($cnt -gt $beforeCount){ return $true }
    Start-Sleep -Milliseconds 400
  }
  return $false
}

function TailLastResult(){
  $lines=@()
  if(Test-Path $EVT){ $lines=Get-Content $EVT -Tail 3 -ErrorAction SilentlyContinue }
  return ($lines -join [Environment]::NewLine)
}



New-Item -ItemType Directory -Force -Path (Split-Path $OUT -Parent) | Out-Null

$summary = New-Object System.Collections.ArrayList

# 1) count monitors
$before1 = 0; if(Test-Path $EVT){ $before1 = (Get-Content $EVT | Measure-Object -Line).Lines }
Add-UserLine 'count my monitors'
$ok1 = Wait-Dispatch -beforeCount $before1 -timeoutSec 20
[void]$summary.Add(('MONITORS_OK='+$ok1))
$tmp1 = TailLastResult
[void]$summary.Add($tmp1)

# 2) write autonamed note
$before2 = 0; if(Test-Path $EVT){ $before2 = (Get-Content $EVT | Measure-Object -Line).Lines }
Add-UserLine 'write a short note to my desktop saying: ALL GREEN'
$ok2 = Wait-Dispatch -beforeCount $before2 -timeoutSec 20
[void]$summary.Add(('WRITE_OK='+$ok2))
$tmp2 = TailLastResult
[void]$summary.Add($tmp2)

# 3) take screenshot
$before3 = 0; if(Test-Path $EVT){ $before3 = (Get-Content $EVT | Measure-Object -Line).Lines }
Add-UserLine 'take a screenshot named auto'
$ok3 = Wait-Dispatch -beforeCount $before3 -timeoutSec 20
[void]$summary.Add(('SCREENSHOT_OK='+$ok3))
$tmp3 = TailLastResult
[void]$summary.Add($tmp3)

$overall = $ok1 -and $ok2 -and $ok3
[void]$summary.Add(('OVERALL='+$overall))
$summary -join ([Environment]::NewLine) | Set-Content -Encoding Ascii -LiteralPath $OUT
Write-Host '=== AUTONOMOUS VERIFY COMPLETE ==='
Write-Host ('Summary -> ' + $OUT)
