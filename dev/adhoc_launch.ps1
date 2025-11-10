$ErrorActionPreference = 'Continue'
$root='C:\bots\ecosys'
$py=Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py='python' }
# ensure packages
& $py -m pip -q install -U fastapi uvicorn | Out-Null

# choose port
$port = 8765
for ($i=0; $i -lt 20; $i++) {
  try {
    $l = New-Object System.Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $port)
    $l.Start(); $l.Stop(); break
  } catch { $port++ }
}

$env:ECOSYS_TOOL_HOST='127.0.0.1'
$env:ECOSYS_TOOL_PORT="$port"

$toolArgs = @('-m','uvicorn','dev.tool_server:app','--host',$env:ECOSYS_TOOL_HOST,'--port',"$port",'--log-level','warning')
$toolProc = Start-Process -PassThru -FilePath $py -ArgumentList $toolArgs -WorkingDirectory $root
$dispProc = Start-Process -PassThru -FilePath $py -ArgumentList @('-m','dev.dispatcher') -WorkingDirectory $root
$routerProc = Start-Process -PassThru -FilePath $py -ArgumentList @('-m','dev.nl_router') -WorkingDirectory $root

$pidObj = [ordered]@{ tool = $toolProc.Id; dispatch = $dispProc.Id; router = $routerProc.Id; port = $port }
$pidPath = Join-Path $root 'reports\AUTONOMOUS_PIDS.json'
($pidObj | ConvertTo-Json) | Set-Content -Encoding Ascii -LiteralPath $pidPath

# Inject test
$tail = Join-Path $root 'reports\chat\exact_tail.jsonl'
if (!(Test-Path $tail)) { New-Item -ItemType File -Path $tail | Out-Null }
$now=[double](Get-Date -Date (Get-Date) -UFormat %s)
Add-Content -Encoding UTF8 -LiteralPath $tail -Value (@{ts=$now; role='user'; text='count my monitors'} | ConvertTo-Json -Compress)

Start-Sleep -Seconds 6
'Tail ecosys markers:'
Select-String -Path $tail -Pattern '\[ecosystem-call\]|\[ecosystem-result\]' -ErrorAction SilentlyContinue | ForEach-Object { $_.Line }
'Router events tail:'
Get-Content -Path (Join-Path $root 'reports\ROUTER_EVENTS.jsonl') -ErrorAction SilentlyContinue -Tail 5
'Dispatch events tail:'
Get-Content -Path (Join-Path $root 'reports\DISPATCH_EVENTS.jsonl') -ErrorAction SilentlyContinue -Tail 5
