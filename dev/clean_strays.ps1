$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# Use literal names for problematic files; escape $ with backtick
$targets = @(
  (Join-Path $repo '`$null'),
  (Join-Path $repo 'CON'),
  (Join-Path $repo '-')
)

foreach ($t in $targets) {
  if (Test-Path -LiteralPath $t) {
    try {
      Remove-Item -LiteralPath $t -Force -ErrorAction Stop
      Write-Host ("Removed: {0}" -f $t)
    } catch {
      $long = "\\?\" + $t
      try {
        Remove-Item -LiteralPath $long -Force -ErrorAction Stop
        Write-Host ("Removed via long path: {0}" -f $t)
      } catch {
        Write-Host ("Failed to remove: {0} : {1}" -f $t, $_.Exception.Message)
      }
    }
  }
}
