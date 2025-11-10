try { [Console]::OutputEncoding=[Text.Encoding]::ASCII } catch {}
Set-Location 'C:\bots\ecosys'
Write-Host '==== OUTPUT (live) ====' -ForegroundColor Green
Start-Job -ScriptBlock { Set-Location 'C:\bots\ecosys'; Get-Content '.\reports\chat\exact_tail.jsonl' -Wait -ErrorAction SilentlyContinue | Select-String -SimpleMatch -Pattern '[ecosystem-result]' | ForEach-Object { Write-Host .Line -ForegroundColor Yellow } } | Out-Null
Start-Job -ScriptBlock { Set-Location 'C:\bots\ecosys'; Get-Content '.\reports\ROUTER_EVENTS.jsonl' -Wait -ErrorAction SilentlyContinue | ForEach-Object {  } } | Out-Null
Start-Job -ScriptBlock { Set-Location 'C:\bots\ecosys'; Get-Content '.\reports\DISPATCH_EVENTS.jsonl' -Wait -ErrorAction SilentlyContinue | ForEach-Object {  } } | Out-Null
Write-Host '[INFO] Tailing results + router + events. Close this window to stop tailing.'
