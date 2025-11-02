# Deduplicate session_tasks by id in logs/tasks.json, ASCII-only write
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$p = Join-Path $repo 'logs\tasks.json'
$ops = Join-Path $repo 'runs\current\ops_log.txt'

$txt = Get-Content -Raw -Path $p
$obj = $txt | ConvertFrom-Json
$seen = @{}
$dedup = @()
$removed = 0
foreach ($it in $obj.session_tasks) {
  $id = $it.id
  if ($seen.ContainsKey($id)) {
    $removed += 1
  } else {
    $seen[$id] = $true
    $dedup += $it
  }
}
$obj.session_tasks = $dedup
$obj.updated_ts = [int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$json = $obj | ConvertTo-Json -Depth 12
Set-Content -Encoding ASCII -Path $p -Value $json
Add-Content -Encoding ASCII -Path $ops -Value ("DEDUP session_tasks removed=" + $removed)
