# C:\bots\ecosys\tools\ui.py
from __future__ import annotations
import os, subprocess, time
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

def hotkey(keys: List[str] | None = None, combo: str | None = None) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    _ensure_focus_lastpid()
    if (not keys) and combo:
        combo = combo.strip().lower()
        parts = [p.strip() for p in combo.split("+") if p.strip()]
        keys = parts
    keys = [k.lower() for k in (keys or [])]
    if not keys:
        return {"ok": False, "error": "no keys/combo provided"}
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
    tools.add("ui.focus_by_pid", focus_by_pid, desc="Focus window by PID and remember as LAST_UI_PID")
    tools.add("ui.focus_by_title", focus_by_title, desc="Focus window by title substring")
    tools.add("ui.wait_title_contains", wait_title_contains, desc="Wait until a window title contains substring")
    tools.add("ui.paste", paste, desc="Paste with cascade and verification")

# Paste cascade with focus escalation and verification

def _get_clip() -> str:
    try:
        import ctypes
        CF_UNICODETEXT = 13
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if user32.OpenClipboard(0):
            try:
                h = user32.GetClipboardData(CF_UNICODETEXT)
                if h:
                    ptr = kernel32.GlobalLock(h)
                    if ptr:
                        text = ctypes.wstring_at(ptr)
                        kernel32.GlobalUnlock(h)
                        return text or ""
            finally:
                user32.CloseClipboard()
    except Exception:
        pass
    return ""


def _set_clip(text: str) -> None:
    try:
        import ctypes
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return
        try:
            user32.EmptyClipboard()
            data = text.encode('utf-16-le') + b"\x00\x00"
            h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            ptr = kernel32.GlobalLock(h)
            ctypes.memmove(ptr, data, len(data))
            kernel32.GlobalUnlock(h)
            user32.SetClipboardData(CF_UNICODETEXT, h)
        finally:
            user32.CloseClipboard()
    except Exception:
        pass


def _normalize_crlf(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n")


def _assert_clip_matches_window(expected: str, max_wait_ms: int = 1200) -> bool:
    exp = _normalize_crlf(expected or "")
    deadline = time.time() + (max_wait_ms/1000.0)
    while time.time() < deadline:
        hotkey(["ctrl", "a"])  # ignore result
        hotkey(["ctrl", "c"])  # ignore result
        w = _normalize_crlf(_get_clip())
        if w == exp:
            return True
        time.sleep(0.08)
    return False


def focus_by_pid(pid: int) -> Dict[str, Any]:
    try:
        subprocess.run(['powershell','-NoProfile','-Sta','-Command', _PS_ACTIVATE_PID, '--', str(int(pid))],
                       shell=False, capture_output=True, text=True, encoding='utf-8', timeout=10)
        os.environ['LAST_UI_PID'] = str(int(pid))
        return {"ok": True, "pid": int(pid)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def focus_by_title(title_substr: str) -> Dict[str, Any]:
    try:
        ps = r"$t='" + title_substr.replace("'","''") + r"'; $p=Get-Process | Where-Object {$_.MainWindowTitle -like '*'+$t+'*'} | Select-Object -First 1; if($p){$ws=New-Object -ComObject WScript.Shell; $ws.AppActivate($p.MainWindowTitle)|Out-Null; 'OK'} else {'NOTFOUND'}"
        c = subprocess.run(['powershell','-NoProfile','-Sta','-Command', ps], capture_output=True, text=True, encoding='utf-8', timeout=10)
        if (c.stdout or '').strip().upper().startswith('OK'):
            return {"ok": True, "title": title_substr}
        return {"ok": False, "error": "title_not_found"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def wait_title_contains(substr: str, timeout_ms: int = 3000) -> Dict[str, Any]:
    try:
        ps = r"$s='" + substr.replace("'","''") + r"'; $d=[DateTime]::UtcNow.AddMilliseconds(" + str(int(timeout_ms)) + r"); while([DateTime]::UtcNow -lt $d){ $p=Get-Process | Where-Object {$_.MainWindowTitle -like '*'+$s+'*'} | Select-Object -First 1; if($p){'OK'; exit 0}; Start-Sleep -Milliseconds 100 }; 'TIMEOUT'"
        c = subprocess.run(['powershell','-NoProfile','-Sta','-Command', ps], capture_output=True, text=True, encoding='utf-8', timeout=(timeout_ms//1000)+2)
        if (c.stdout or '').strip().upper().startswith('OK'):
            return {"ok": True}
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def paste(max_retries: int = 3) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    _ensure_focus_lastpid()
    clip = _get_clip() or ""
    last_err = None
    for attempt in range(max_retries):
        r1 = hotkey(["ctrl","v"])
        if r1.get("ok") and _assert_clip_matches_window(clip):
            return {"ok": True, "method": "ctrl-v", "attempt": attempt+1}
        r2 = hotkey(["shift","insert"])
        if r2.get("ok") and _assert_clip_matches_window(clip):
            return {"ok": True, "method": "shift-insert", "attempt": attempt+1}
        hotkey(["shift","f10"])  # context menu
        type_text("p")
        if _assert_clip_matches_window(clip):
            return {"ok": True, "method": "uia-context", "attempt": attempt+1}
        type_text(clip)
        if _assert_clip_matches_window(clip):
            return {"ok": True, "method": "typed-fallback", "attempt": attempt+1}
        hotkey(["alt","tab"])  # cycle focus
        hotkey(["win","up"])   # maximize if possible
        last_err = "paste verification failed"
    return {"ok": False, "error": last_err or "paste failed"}
