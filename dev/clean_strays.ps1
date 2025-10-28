$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$targets = @(
  "$repo\$null",
  "$repo\CON",
  "$repo\-"
)

foreach ($t in $targets) {
  if (Test-Path -LiteralPath $t) {
    try {
      # Try normal delete
      Remove-Item -LiteralPath $t -Force -ErrorAction Stop
      Write-Host ("Removed: {0}" -f $t)
    } catch {
      # Try extended path prefix
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
