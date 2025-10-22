# C:\bots\ecosys\tools\winui.py
from __future__ import annotations
import subprocess
from typing import Any, Dict, Optional

_PS_FOCUS = r'''
param([int]$Pid = 0, [string]$TitleSubstr = "")
Add-Type -Namespace Win -Name Native -MemberDefinition @"
using System;
using System.Runtime.InteropServices;
public static class Native {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}
"@
$target = $null
if ($Pid -gt 0) {
  $p = Get-Process | Where-Object { $_.Id -eq $Pid } | Select-Object -First 1
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
    args = ["powershell","-NoProfile","-Sta","-Command", _PS_FOCUS, "-Pid", str(pid or 0), "-TitleSubstr", title_substr or ""]
    c = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    out = (c.stdout or "").strip()
    return {"ok": out.startswith("ok:"), "stdout": out, "stderr": c.stderr, "code": c.returncode}

def register(tools) -> None:
    tools.add("win.focus_window", focus_window, desc="Focus a window (by pid or title substring, or newest with a main window)")
