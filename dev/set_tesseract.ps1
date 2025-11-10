$t = 'C:\Program Files\Tesseract-OCR'
$exe = Join-Path $t 'tesseract.exe'
if (!(Test-Path $exe)) { Write-Host ('ERROR: not found -> ' + $exe) -ForegroundColor Red; exit 1 }
$userPath = [Environment]::GetEnvironmentVariable('Path','User')
if (-not $userPath) { $userPath = '' }
$has = ($userPath -split ';') -contains $t
if (-not $has) {
  $newUserPath = ($userPath.TrimEnd(';') + ';' + $t)
  setx PATH $newUserPath | Out-Null
  Write-Host ('Added to user PATH: ' + $t) -ForegroundColor Green
} else {
  Write-Host 'Tesseract already in user PATH (user scope).' -ForegroundColor Yellow
}
setx TESSDATA_PREFIX (Join-Path $t 'tessdata') | Out-Null
$env:PATH = $env:PATH + ';' + $t
$env:TESSDATA_PREFIX = Join-Path $t 'tessdata'
& $exe --version
