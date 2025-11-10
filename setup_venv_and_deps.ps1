$ErrorActionPreference = 'Stop'
Set-Location 'C:\bots\ecosys'

function Ensure-Venv {
    param(
        [string]$Path = '.venv'
    )
    $root = (Resolve-Path '.').Path
    $pyPath = Join-Path $root "$Path\Scripts\python.exe"
    if (-not (Test-Path $pyPath)) {
        try { & py -3 -m venv $Path }
        catch {
            try { & python -m venv $Path }
            catch { throw 'Could not create venv. Install Python 3 or ensure py/python is in PATH.' }
        }
    }
    return $pyPath
}

$py = Ensure-Venv
& $py -m pip install --upgrade pip
& $py -m pip install --upgrade pyautogui keyboard mouse mss pillow pytesseract pygetwindow requests playwright pywin32
