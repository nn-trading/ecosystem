param([int]$Keep=30)
$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent $PSScriptRoot
$dstBase = "C:\bots\backups"
$logs = Join-Path $repo "logs"
$events = Join-Path $repo "workspace\logs\events.jsonl"
New-Item -ItemType Directory -Force -Path $dstBase | Out-Null
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$dst = Join-Path $dstBase $ts
New-Item -ItemType Directory -Force -Path $dst | Out-Null
if (Test-Path $logs) { Copy-Item -Recurse -Force $logs $dst }
if (Test-Path $events) { Copy-Item -Force $events (Join-Path $dst "events.jsonl") }

$probeDir = Join-Path $logs "probes"
$latestProbe = $null
if (Test-Path $probeDir) {
  $latestProbe = Get-ChildItem -Path $probeDir -Filter *.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
$eventsSize = (Get-Item $events -ErrorAction SilentlyContinue).Length
$eventsLines = 0
try { $eventsLines = (Get-Content $events -ReadCount 0 | Measure-Object -Line).Lines } catch {}
$snap = [ordered]@{
  ts = (Get-Date).ToString("o")
  repo = $repo
  events_path = $events
  events_size = $eventsSize
  events_lines = $eventsLines
  latest_probe = if ($latestProbe) { $latestProbe.Name } else { $null }
}
$snap | ConvertTo-Json -Depth 5 | Out-File -FilePath (Join-Path $dst "snapshot.json") -Encoding UTF8

$dirs = Get-ChildItem $dstBase -Directory | Sort-Object Name -Descending
$toRemove = $dirs | Select-Object -Skip $Keep
foreach ($d in $toRemove) { Remove-Item -Recurse -Force $d.FullName }
