try { [Console]::OutputEncoding=[Text.Encoding]::ASCII } catch {}
Set-Location 'C:\bots\ecosys'
 = '.\reports\chat\exact_tail.jsonl'
function Append-Tail([string]){
  try{
    =[IO.File]::Open(,[IO.FileMode]::Append,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite)
    =New-Object IO.StreamWriter(,[Text.Encoding]::ASCII)
    .WriteLine(); .Flush(); .Dispose(); .Dispose()
  } catch { Add-Content -Encoding Ascii -Path  -Value  }
}
Write-Host '[Bridge] Watching DISPATCH_EVENTS for results' -ForegroundColor Green
Get-Content '.\reports\DISPATCH_EVENTS.jsonl' -Wait -ErrorAction SilentlyContinue | ForEach-Object {
   = 
  try {
     =  | ConvertFrom-Json -ErrorAction Stop
      = .call.tool
        = .result.ok
      = .result.path
     = .result.extra
     = 'unknown'
    if ( -eq True) {  = 'ok' }
    elseif ( -eq False) {  = 'fail' }
     = '[ecosystem-result] ' +  + ' -> ' + 
    if ()  {  += ' | path: ' +  }
    if () {  += ' | extra: ' + (( | Out-String).Trim()) }
    Append-Tail 
  } catch {}
}
