from __future__ import annotations
import subprocess

SAFE_PREFIXES = (
    "Get-ChildItem", "Get-Content", "Select-String", "Test-Path",
    "Get-Process", "Stop-Process", "Get-Service",
    "Get-ItemProperty", "Get-Date", "Get-Location", "Set-Location",
    "New-Item", "Copy-Item", "Move-Item", "Remove-Item",
    "Invoke-WebRequest", "Invoke-RestMethod"
)

def run(cmd: str, danger: bool = False, timeout: int = 600) -> dict:
    if not cmd:
        return {"ok": False, "error": "empty command"}
    if not danger:
        first = (cmd.strip().split() or [""])[0]
        if not any(first.lower().startswith(p.lower()) for p in SAFE_PREFIXES):
            return {"ok": False, "error": f"danger_mode off: '{first}' not allowed"}
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout, shell=False
        )
        return {
            "ok": completed.returncode == 0,
            "code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
