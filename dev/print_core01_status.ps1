param([switch]$Details)
Set-StrictMode -Version 2; $ErrorActionPreference='Continue'
Set-Location -LiteralPath 'C:\bots\ecosys'
Write-Host 'CORE01 SUMMARY:'
if(Test-Path 'reports\CORE01_FIX_SUMMARY.txt'){
  Get-Content 'reports\CORE01_FIX_SUMMARY.txt' | Select-Object -Last 8
}else{'no summary'}
Write-Host 'PING:'
try{ (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8766/ping' -TimeoutSec 5).Content }catch{ $_.Exception.Message }
Write-Host 'EVENTS:'
$ev='reports\DISPATCH_EVENTS.jsonl'
if(Test-Path $ev){ Get-Item $ev | Select-Object FullName,Length,LastWriteTime; if($Details){ Write-Host 'last 5 lines:'; Get-Content $ev -Tail 5 } } else {'no events'}
Write-Host 'TAIL MARKERS (main):'
$main='reports\chat\exact_tail.jsonl'
if(Test-Path $main){ Select-String -Path $main -Pattern '\[ecosystem-result\]' -SimpleMatch | Select-Object -Last 3 | ForEach-Object { $_.Line } }
Write-Host 'TAIL MARKERS (shadow):'
$shadow='reports\chat\exact_tail_shadow.jsonl'
if(Test-Path $shadow){ Select-String -Path $shadow -Pattern '\[ecosystem-result\]' -SimpleMatch | Select-Object -Last 3 | ForEach-Object { $_.Line } }
