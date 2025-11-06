$ErrorActionPreference = 'Stop'
$txt = ''
if (Test-Path 'var\pytest_output.txt') {
  $txt = Get-Content 'var\pytest_output.txt' -Raw
}
$p = 0; $s = 0; $w = 0
if ($txt) {
  foreach ($ch in $txt.ToCharArray()) {
    if ($ch -eq '.') { $p++ }
    elseif ($ch -eq 's') { $s++ }
  }
  try {
    $w = (Select-String -Path 'var\pytest_output.txt' -Pattern '(?i)warning' | Measure-Object).Count
  } catch { $w = 0 }
}
$out = "pytest: $p passed, $s skipped, $w warnings"
$enc = New-Object System.Text.ASCIIEncoding
[System.IO.File]::WriteAllText('var\pytest_summary.txt', $out, $enc)
