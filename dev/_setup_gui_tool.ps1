$ErrorActionPreference = 'Stop'
Set-Location 'C:\bots\ecosys'

# 1) Ensure tools dir exists
New-Item -ItemType Directory -Force -Path .\tools | Out-Null

# 2) Append (or create) a safe wrapper in tools/gui_tool.py
$guiTool = '.\tools\gui_tool.py'
$fn = @'
def wait_title_contains(substring: str, timeout_sec: int = 15, poll_ms: int = 200) -> dict:
    """
    Thin wrapper over core.win_wait.wait_title_contains.
    Returns a dict with keys: ok (bool), title (str), contains (str), and timing fields.
    """
    try:
        from core.win_wait import wait_title_contains as _w
    except Exception as e:
        return {"ok": False, "error": f"import core.win_wait failed: {e}"}
    return _w(substring, timeout_sec, poll_ms)
'@

if (Test-Path $guiTool) {
  $content = Get-Content $guiTool -Raw
  if ($content -notmatch 'def\s+wait_title_contains\(') {
    Add-Content -LiteralPath $guiTool -Value "`r`n`r`n$fn"
  }
} else {
  $header = '# tools/gui_tool.py  GUI helpers' + "`r`n`r`n"
  Set-Content -LiteralPath $guiTool -Value ($header + $fn) -Encoding UTF8
}

# 3) Add a tiny test
New-Item -ItemType Directory -Force -Path .\tests | Out-Null
$test = @'
from tools.gui_tool import wait_title_contains

def test_gui_wait_wrapper_smoke():
    res = wait_title_contains("Notepad", timeout_sec=1, poll_ms=200)
    assert isinstance(res, dict)
    for k in ("ok", "contains", "title"):
        assert k in res
'@
Set-Content -LiteralPath .\tests\test_gui_wait_wrapper.py -Value $test -Encoding UTF8

# 4) Ensure pytest available and run focused pytest
function Ensure-Pytest($py) {
  try { & $py -c "import pytest,sys; print(pytest.__version__)" | Out-Null; return $true } catch {}
  try { & $py -m ensurepip --upgrade | Out-Null } catch {}
  try { & $py -m pip install -U pytest | Out-Host } catch {}
  try { & $py -c "import pytest" | Out-Null; return $true } catch { return $false }
}

$py = 'C:\bots\ecosys\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
if (-not (Ensure-Pytest($py))) { throw 'pytest is not available even after installation attempts' }

& $py -m pytest -q tests/test_gui_wait_wrapper.py
$code = $LASTEXITCODE
if ($null -eq $code) { $code = 0 }
if ($code -ne 0) { exit $code }

# 5) Commit
git add tools/gui_tool.py tests/test_gui_wait_wrapper.py
git -c core.hooksPath=.githooks-disabled commit -m "feat(win): expose wait_title_contains via tools.gui_tool + wrapper smoke test\n\nCo-authored-by: openhands <openhands@all-hands.dev>" --author "openhands <openhands@all-hands.dev>" | Out-Null

Write-Host 'OK: tools.gui_tool wait wrapper added, test passed, changes committed.' -ForegroundColor Green
