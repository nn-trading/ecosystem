# C:\bots\ecosys\tools\winui.py
from __future__ import annotations
import subprocess, time, tempfile, os
from typing import Any, Dict, Optional

_PS_FOCUS = r'''
param([int]$TargetPid = 0, [string]$TitleSubstr = "")
Add-Type -Namespace Win -Name Native -MemberDefinition @"
using System;
using System.Runtime.InteropServices;
public static class Native {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}
"@
$target = $null
if ($TargetPid -gt 0) {
  $p = Get-Process | Where-Object { $_.Id -eq $TargetPid } | Select-Object -First 1
  if ($p -and $p.MainWindowHandle -ne 0) { $target = $p }
}
elseif ($TitleSubstr -ne "") {
  $p = Get-Process | Where-Object { $_.MainWindowTitle -like "*$TitleSubstr*" } | Sort-Object StartTime | Select-Object -Last 1
  if ($p -and $p.MainWindowHandle -ne 0) { $target = $p }
}
else {
  $p = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 } | Sort-Object StartTime | Select-Object -Last 1
  if ($p) { $target = $p }
}
if ($null -ne $target) {
  [Win.Native]::ShowWindowAsync($target.MainWindowHandle, 9) | Out-Null  # SW_RESTORE
  [Win.Native]::SetForegroundWindow($target.MainWindowHandle) | Out-Null
  "ok:$($target.Id):$($target.MainWindowTitle)"
} else {
  "no-window"
}
'''

def focus_window(pid: Optional[int] = None, title_substr: Optional[str] = None) -> Dict[str, Any]:
    # Run the PowerShell helper as a temporary script so named params bind correctly
    out = ""; err = ""; code = -1
    def _run_once() -> Dict[str, Any]:
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".ps1", encoding="utf-8") as f:
                f.write(_PS_FOCUS)
                path = f.name
            try:
                args = [
                    "powershell","-NoProfile","-Sta","-File", path,
                    "-TargetPid", str(int(pid or 0)),
                    "-TitleSubstr", title_substr or "",
                ]
                c = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
            finally:
                try: os.remove(path)
                except Exception: pass
            return {"stdout": (c.stdout or "").strip(), "stderr": c.stderr, "code": c.returncode}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "code": -1}
    last: Dict[str, Any] = {}
    for _ in range(3):
        last = _run_once()
        out = last.get("stdout", ""); err = last.get("stderr", ""); code = int(last.get("code", -1))
        if out.startswith("ok:"):
            break
        time.sleep(0.2)
    return {"ok": out.startswith("ok:"), "stdout": out, "stderr": err, "code": code}


def activate_pid(pid: int) -> Dict[str, Any]:
    return focus_window(pid=pid)


def activate_title_contains(substr: str) -> Dict[str, Any]:
    return focus_window(title_substr=substr or "")


def wait_title_contains(substr: str, timeout: int = 10) -> Dict[str, Any]:
    try:
        t_end = time.time() + max(1, int(timeout))
    except Exception:
        t_end = time.time() + 10
    last: Dict[str, Any] = {"ok": False, "error": "not found"}
    while time.time() < t_end:
        r = focus_window(title_substr=substr or "")
        last = r if isinstance(r, dict) else {"ok": False}
        if last.get("ok"):
            return {"ok": True, "found": True, "title": last.get("stdout", "")}
        time.sleep(0.2)
    last["timeout"] = True
    return last


def register(tools) -> None:
    tools.add("win.focus_window", focus_window, desc="Focus a window (by pid or title substring, or newest with a main window)")
    tools.add("win.activate_pid", activate_pid, desc="Activate window by pid")
    tools.add("win.activate_title_contains", activate_title_contains, desc="Activate window by title substring")
    tools.add("win.wait_title_contains", wait_title_contains, desc="Wait for window by title substring")

