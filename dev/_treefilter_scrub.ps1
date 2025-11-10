$ErrorActionPreference = 'Stop'
# Remove api_key.txt if present
if (Test-Path -LiteralPath 'api_key.txt') {
  Remove-Item -Force -LiteralPath 'api_key.txt'
}
# Replace any OpenAI-style keys in specific scripts (and any other files if needed)
$files = @(
  'dev\oh_autofix.ps1',
  'dev\oh_grand_test.ps1',
  'dev\oh_use_key_and_launch.ps1'
)
foreach ($f in $files) {
  if (Test-Path -LiteralPath $f) {
    try {
      $txt  = Get-Content -LiteralPath $f -Raw
      $txt2 = [regex]::Replace($txt, 'sk-[A-Za-z0-9_\-]{20,}', 'REDACTED')
      if ($txt2 -ne $txt) {
        Set-Content -Encoding Ascii -LiteralPath $f -Value $txt2
      }
    } catch {}
  }
}
