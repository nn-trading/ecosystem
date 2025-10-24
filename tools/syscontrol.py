# C:\bots\ecosys\tools\syscontrol.py
from __future__ import annotations
import os, re, time, shutil, subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Safety: default ON during dev (set AGENT_DANGER_MODE=0 to block)
DANGER = os.environ.get("AGENT_DANGER_MODE", "1") == "1"

# ---------- tiny WinUI helpers (inline so launch can act autonomously) ----------
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

def _focus_pid(pid: int) -> None:
    try:
        subprocess.run(
            ['powershell','-NoProfile','-Sta','-Command', _PS_ACTIVATE_PID, '--', str(pid)],
            shell=False, capture_output=True, text=True, encoding="utf-8", timeout=10
        )
    except Exception:
        pass

def _sendkeys(seq: str) -> Dict[str, Any]:
    try:
        c = subprocess.run(
            'powershell -Sta -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; Start-Sleep -Milliseconds 100; $ws.SendKeys([Console]::In.ReadToEnd())"',
            input=seq, shell=True, capture_output=True, text=True, encoding="utf-8"
        )
        if c.returncode == 0:
            return {"ok": True, "sent": seq}
        return {"ok": False, "error": c.stderr or f"sendkeys exited {c.returncode}"}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

def _clip_get() -> Dict[str, Any]:
    c = subprocess.run(
        'powershell -Sta -NoProfile -Command "[Console]::OutputEncoding=[Text.UTF8Encoding]::UTF8; Get-Clipboard -Raw"',
        shell=True, capture_output=True, text=True, encoding="utf-8"
    )
    if c.returncode == 0:
        out = c.stdout[:-2] if c.stdout.endswith("\r\n") else c.stdout
        return {"ok": True, "text": out}
    return {"ok": False, "error": c.stderr or f"ps exited {c.returncode}"}

def _esc_text(t: str) -> str:
    return t.replace("{","{{}").replace("}","{}}")

# ----------- natural-language parser for post-launch UI actions -----------
_STOP_TOKENS = r"(?:\bthen\b|\band\b|\bafter\b|\bnext\b|$)"

def _extract_text_to_type(phrase: str) -> Optional[str]:
    # quoted text: "hello world" or 'hello world'
    m = re.search(r'type\s*["“](.+?)["”]\s*' + _STOP_TOKENS, phrase, flags=re.I)
    if m: return m.group(1)
    m = re.search(r"type\s+'(.+?)'\s*" + _STOP_TOKENS, phrase, flags=re.I)
    if m: return m.group(1)
    # bare token(s): type 123  or  type hello
    m = re.search(r"type\s+(.+?)\s*" + _STOP_TOKENS, phrase, flags=re.I)
    if m:
        # stop at keywords like copy/paste/press etc.
        txt = re.split(r"\s+(?:copy|paste|press|hit|ctrl|control|select|all)\b", m.group(1), maxsplit=1, flags=re.I)[0]
        return txt.strip()
    return None

def _wants_select_all(phrase: str) -> bool:
    return bool(re.search(r"(ctrl\+?a|select\s+all)", phrase, flags=re.I))

def _wants_copy(phrase: str) -> bool:
    return bool(re.search(r"\bcopy\b|\bctrl\+?c\b", phrase, flags=re.I))

def _wants_paste(phrase: str) -> bool:
    return bool(re.search(r"\bpaste\b|\bctrl\+?v\b", phrase, flags=re.I))

def _post_launch_actions(pid: int, phrase: str) -> Dict[str, Any]:
    """
    Interpret phrases like:
      'type 123 then copy', 'type "hello world"', 'type 42, ctrl+a, ctrl+c'
    Generic — works for any text control of the focused app.
    """
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}

    phrase = phrase.strip()
    if not phrase:
        return {"ok": True, "info": "no post-launch actions"}

    # Bring the window up and give it a moment
    _focus_pid(pid)
    time.sleep(0.25)

    typed = None
    target = _extract_text_to_type(phrase)
    if target:
        typed = target
        r = _sendkeys(_esc_text(target))
        if not r.get("ok"):
            return r

    if _wants_select_all(phrase):
        r = _sendkeys("^a")
        if not r.get("ok"):
            return r

    clip: Optional[str] = None
    if _wants_copy(phrase):
        r = _sendkeys("^c")
        if not r.get("ok"):
            return r
        g = _clip_get()
        if g.get("ok"):
            clip = g["text"]
        else:
            return g

    if _wants_paste(phrase):
        r = _sendkeys("^v")
        if not r.get("ok"):
            return r

    out: Dict[str, Any] = {"ok": True, "typed": typed, "copied": clip}
    return out

# --------------------- public tools ---------------------
def set_env(name: str, value: str) -> Dict[str, Any]:
    os.environ[name] = value
    return {"ok": True, "name": name, "value": value}

def launch(exe: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Launch an executable (e.g., 'notepad', 'mspaint', or a full path).
    If extra args are present and look like plain English instructions
    (e.g., 'and type 123 then copy'), we will perform those UI actions
    on the newly launched window using SendKeys/clipboard, and return
    the results in the JSON (typed/copied fields).
    """
    args = args or []
    exe = _sanitize_exe(exe)
    resolved = exe
    if not Path(resolved).exists():
        cand = shutil.which(resolved) or (shutil.which(resolved + ".exe") if not resolved.lower().endswith(".exe") else None)
        if cand:
            resolved = cand
    if not resolved:
        return {"ok": False, "error": f"executable not found: {exe}"}

    try:
        proc = subprocess.Popen([resolved, *[a for a in args if a]], creationflags=subprocess.CREATE_NEW_CONSOLE)
    except FileNotFoundError:
        return {"ok": False, "error": f"executable not found: {exe} (resolved: {resolved})"}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

    os.environ["LAST_UI_PID"] = str(proc.pid)
    os.environ["LAST_LAUNCH_PID"] = str(proc.pid)

    result: Dict[str, Any] = {"ok": True, "exe": resolved, "args": args, "pid": proc.pid}

    # If arguments look like natural-language instructions, run post-launch UI actions.
    if args:
        phrase = " ".join(args)
        # Heuristic: if it contains 'type'/'copy'/'paste'/'ctrl', treat as UI phrase.
        if re.search(r"\b(type|copy|paste|ctrl\+?a|ctrl\+?c|ctrl\+?v|select\s+all)\b", phrase, flags=re.I):
            ui_res = _post_launch_actions(proc.pid, phrase)
            result["ui"] = ui_res

    return result

def register(tools) -> None:
    tools.add("sysctl.set_env", set_env, desc="Set an environment variable in the current process")
    tools.add("sysctl.launch",  launch,  desc="Launch a program; can also parse phrases like 'type 123 then copy' and execute them in the launched app")

