$ErrorActionPreference = 'Stop'
$repo = 'C:\bots\ecosys'
Set-Location $repo
$prov = ((Get-Content .\config\llm.yaml | Where-Object {$_ -match '^provider:'}) -replace 'provider:\s*','').Trim()
$model = ((Get-Content .\config\llm.yaml | Where-Object {$_ -match '^model:'}) -replace 'model:\s*','').Trim()
$probePath = Resolve-Path .\reports\llm\openai_gpt5_probe.txt
$dbPath = Resolve-Path .\var\events.db
Write-Host ("provider_now: $prov")
Write-Host ("model_now: $model")
Write-Host ("probe_file: $probePath")
Write-Host ("db_path: $dbPath")
Write-Host 'PR_COMPARE: https://github.com/nn-trading/ecosystem/compare/main...fix/gpt5-primary-and-multiproviders?expand=1'
