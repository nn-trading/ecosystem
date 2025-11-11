$ErrorActionPreference = 'Stop'
Set-Location 'C:\bots\ecosys'

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

New-Item -ItemType Directory -Force -Path .\reports\tests | Out-Null

$py = 'C:\bots\ecosys\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

# Ensure pytest is installed
try {
  & $py -c "import pytest" 2>$null
} catch {
  & $py -m pip install -U pytest | Out-Host
}

# Run pytest and tee output to file
& $py -m pytest -q --maxfail=1 --disable-warnings --junitxml .\reports\tests\junit.xml 2>&1 | Tee-Object .\reports\tests\pytest_console.txt
$code = $LASTEXITCODE
if ($null -eq $code) { $code = 0 }
Write-Host ("PYTEST_EXIT={0}" -f $code)
exit $code
