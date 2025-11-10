try {
  [Console]::OutputEncoding=[Text.Encoding]::UTF8
  [Console]::InputEncoding=[Text.Encoding]::UTF8
} catch {}
$ErrorActionPreference = 'Continue'
Set-Location 'C:\bots\ecosys'
$src = '.\reports\DISPATCH_EVENTS.jsonl'
if (!(Test-Path $src)) { New-Item -ItemType File -Force -Path $src | Out-Null }
$seen = @{}
Write-Host '==== ASSISTANT (live) ====' -ForegroundColor Cyan

try {
  Get-Content $src -Wait -ErrorAction Stop | ForEach-Object {
    try {
      $j = $_ | ConvertFrom-Json -ErrorAction Stop
      $tool  = $j.call.tool
      $ok    = $j.result.ok
      $path  = $j.result.path
      $role  = $j.role
      $delta = $j.delta
      $state = if ($ok -eq $true) { 'ok' } elseif ($ok -eq $false) { 'fail' } else { '?' }

      $msg = $null
      foreach ($k in 'say','message','text','content') {
        if ($j.PSObject.Properties.Name -contains $k -and $j.$k) { $msg = $j.$k; break }
        if ($j.result -and ($j.result.PSObject.Properties.Name -contains $k) -and $j.result.$k) { $msg = $j.result.$k; break }
        if ($j.result.extra -and ($j.result.extra.PSObject.Properties.Name -contains $k) -and $j.result.extra.$k) { $msg = $j.result.extra.$k; break }
        if ($delta -and ($delta.PSObject.Properties.Name -contains $k) -and $delta.$k) { $msg = $delta.$k; break }
      }
      if ($role -eq 'assistant' -and $j.content) { $msg = $j.content }
      if ($msg) { $msg = ($msg | Out-String).Trim() }

      if ($msg) {
        Write-Host ('Assistant: {0}' -f $msg)
      } elseif ($tool -eq 'monitors' -and $j.result.monitors) {
        Write-Host ('Assistant: I detect {0} monitor(s).' -f $j.result.monitors)
      } elseif ($tool -eq 'screenshot' -and $path) {
        Write-Host ('Assistant: Screenshot saved -> {0}' -f $path)
      } elseif ($tool -eq 'write' -and $path) {
        $fname = [System.IO.Path]::GetFileName($path)
        if ($fname -notlike 'auto_*' -and -not $seen.ContainsKey($path)) {
          $seen[$path] = $true
          Write-Host ('Assistant: Wrote -> {0}' -f $path)
        }
      } elseif ($tool) {
        Write-Host ('Assistant: {0} -> {1}' -f $tool, $state)
      }
    } catch {
      Write-Host ('Viewer parse error: {0}' -f $_.Exception.Message) -ForegroundColor DarkYellow
    }
  }
} catch {
  Write-Host ('Viewer error: {0}' -f $_.Exception.Message) -ForegroundColor Red
  Read-Host 'Press Enter to close'
}
