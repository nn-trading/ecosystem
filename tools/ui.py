# C:\bots\ecosys\tools\ui.py
from __future__ import annotations
import os, subprocess
from typing import Any, Dict, List

# Default to enabled (set AGENT_DANGER_MODE=0 to block)
DANGER = os.environ.get("AGENT_DANGER_MODE", "1") == "1"

# PowerShell helper to foreground a window by PID
_PS_ACTIVATE_PID = r"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}
"@;

param([int]$Pid)

$handle = 0
for ($i=0; $i -lt 30; $i++) {
  try {
    $p = Get-Process -Id $Pid -ErrorAction SilentlyContinue
    if ($p -and $p.MainWindowHandle -ne 0) { $handle = $p.MainWindowHandle; break }
  } catch {}
  Start-Sleep -Milliseconds 150
}

if ($handle -eq 0) {
  try {
    $p = Get-Process -Id $Pid -ErrorAction SilentlyContinue
    if ($p -and $p.MainWindowTitle -and $p.MainWindowTitle.Length -gt 0) {
      $ws = New-Object -ComObject WScript.Shell
      $ws.AppActivate($p.MainWindowTitle) | Out-Null
      Start-Sleep -Milliseconds 120
      "OK"; exit 0
    }
  } catch {}
  "NOHWND"; exit 2
}

[void][Win32]::ShowWindowAsync([IntPtr]$handle, 9)
Start-Sleep -Milliseconds 120
[void][Win32]::SetForegroundWindow([IntPtr]$handle)
Start-Sleep -Milliseconds 120
"OK"
exit 0
"""

def _ensure_focus_lastpid() -> None:
    pid = os.environ.get("LAST_UI_PID") or os.environ.get("LAST_LAUNCH_PID")
    if not pid:
        return
    try:
        subprocess.run(
            ['powershell','-NoProfile','-Sta','-Command', _PS_ACTIVATE_PID, '--', str(int(pid))],
            shell=False, capture_output=True, text=True, encoding="utf-8", timeout=10
        )
    except Exception:
        pass

def _ps_sendkeys(seq: str) -> Dict[str, Any]:
    try:
        c = subprocess.run(
            'powershell -Sta -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; Start-Sleep -Milliseconds 120; $ws.SendKeys([Console]::In.ReadToEnd())"',
            input=seq, shell=True, capture_output=True, text=True, encoding="utf-8"
        )
        if c.returncode == 0:
            return {"ok": True, "sent": seq}
        return {"ok": False, "error": c.stderr or f"ps exited {c.returncode}"}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

def _escape_text_for_sendkeys(text: str) -> str:
    return text.replace("{", "{{}").replace("}", "{}}")

def type_text(text: str) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    _ensure_focus_lastpid()
    seq = _escape_text_for_sendkeys(text)
    return _ps_sendkeys(seq)

_SPECIALS = {
    "esc": "{ESC}",
    "enter": "~",
    "tab": "{TAB}",
    "backspace": "{BS}",
    "delete": "{DEL}",
    "left": "{LEFT}",
    "right": "{RIGHT}",
    "up": "{UP}",
    "down": "{DOWN}",
}

def hotkey(keys: List[str]) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    _ensure_focus_lastpid()
    keys = [k.lower() for k in keys]
    if keys == ["esc"]:
        return _ps_sendkeys(_SPECIALS["esc"])
    mods = ""
    if "ctrl" in keys:  mods += "^"
    if "shift" in keys: mods += "+"
    if "alt" in keys:   mods += "%"
    target = None
    for k in reversed(keys):
        if k not in ("ctrl", "shift", "alt", "win"):
            target = k
            break
    if not target:
        return {"ok": False, "error": "no target key in hotkey"}
    if target in _SPECIALS:
        seq = mods + _SPECIALS[target]
    else:
        seq = mods + target
    return _ps_sendkeys(seq)

def register(tools) -> None:
    tools.add("ui.type_text", type_text, desc="Type text into the active window (auto-focuses last launched app)")
    tools.add("ui.hotkey",    hotkey,    desc="Send a hotkey to the active window (auto-focuses last launched app)")
