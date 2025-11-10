param()
$ErrorActionPreference = "Stop"
$ROOT = "C:\bots\ecosys"
Set-Location $ROOT

function Write-Ascii([string]$Path, [string]$Text){
  $dir=Split-Path -Parent $Path; if($dir){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [IO.File]::WriteAllText($Path,$Text,[Text.Encoding]::ASCII)
}

# --- venv + deps (UI/screen) ---
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv } else { python -m venv .venv }
  $py = ".\.venv\Scripts\python.exe"
}
& $py -m pip install -U pip wheel >$null 2>&1
# Minimal, stable set for Windows UI/screen:
& $py -m pip install pywin32 mss pillow screeninfo keyboard >$null 2>&1

# --- local tools: monitors/windows/screenshot ---
$newTools = @'
import os, time, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "reports" / "screens"
OUTDIR.mkdir(parents=True, exist_ok=True)

def count_monitors():
    try:
        from screeninfo import get_monitors
        return len(get_monitors())
    except Exception:
        try:
            import ctypes
            SM_CMONITORS = 80
            return ctypes.windll.user32.GetSystemMetrics(SM_CMONITORS)
        except Exception:
            return -1

def count_windows():
    try:
        import win32gui
        def visible(hwnd):
            try:
                return win32gui.IsWindowVisible(hwnd) and bool(win32gui.GetWindowText(hwnd))
            except Exception:
                return False
        wins = []
        def cb(hwnd, extra):
            if visible(hwnd): wins.append(hwnd)
        win32gui.EnumWindows(cb, None)
        return len(wins)
    except Exception:
        return -1

def screenshot(path=None):
    ts = time.strftime("%Y%m%d_%H%M%S")
    if not path:
        path = OUTDIR / f"shot_{ts}.png"
    try:
        from mss import mss
        with mss() as sct:
            sct.shot(output=str(path))
        return str(path)
    except Exception:
        # very basic fallback via Pillow grabbing the primary screen
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(str(path))
            return str(path)
        except Exception as e:
            return f"(screenshot error: {e})"
'@
Write-Ascii ".\dev\local_tools.py" $newTools

# --- brain chat shell with tools + status ---
$newShell = @'
import os, sys, json, time, subprocess, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)
LOG = ROOT / "logs" / "start_stdout.log"

from importlib import import_module
lt = import_module("dev.local_tools")

MODEL = os.environ.get("MODEL_NAME","gpt-5")

def asc(s): return (s or "").encode("ascii","ignore").decode("ascii")

def append(role, text):
    line = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "role": role, "text": asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f: f.write(json.dumps(line, ensure_ascii=True)+"\n")

def try_planner(q):
    py = str(ROOT/".venv/Scripts/python.exe")
    if not pathlib.Path(py).exists(): py = "python"
    try: subprocess.run([py, "dev/eco_cli.py", "ask", q], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    try: subprocess.run([py, "dev/core02_planner.py", "apply"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def llm_answer(q):
    key_path = ROOT/"api_key.txt"
    key = key_path.read_text().strip() if key_path.exists() else os.environ.get("OPENAI_API_KEY","")
    if not key: return "(no assistant reply yet  set OPENAI_API_KEY or put key into api_key.txt)"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        sys_prompt = (
            "You are the Ecosystem Brain on Windows. Be concise and helpful. "
            "If the user asks for an action on the PC, state what you will do and keep it short."
        )
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"system","content":sys_prompt},{"role":"user","content":q}]
        )
        return asc((r.choices[0].message.content or "").strip())
    except Exception as e:
        return asc(f"(model error: {e})")

def poll_tail(timeout=20, min_wait=1.0):
    t0 = time.time()
    while time.time()-t0 < min_wait: time.sleep(0.2)
    end = t0 + timeout
    while time.time() < end:
        try:
            lines = TAIL.read_text(encoding="ascii", errors="ignore").splitlines()
            for ln in reversed(lines):
                try:
                    o=json.loads(ln)
                    if o.get("role") in ("assistant","brain") and o.get("text") and not str(o.get("text",""))[:5]=="echo:":
                        return o["text"]
                except: pass
        except: pass
        time.sleep(0.4)
    return None

def status_report():
    ok = {"brain": False, "comms": False, "jobs": False}
    try:
        if LOG.exists():
            tail = LOG.read_text(errors="ignore")[-20000:]
            if "CORE-02 inbox loop started" in tail: ok["brain"] = True
            if "Chat rotate started" in tail or "Bridges ready" in tail: ok["comms"] = True
            if "JobsWorker started" in tail: ok["jobs"] = True
    except: pass
    return f"Agents -> Brain:{ok['brain']}  Comms:{ok['comms']}  JobsWorker:{ok['jobs']}"

def handle_local(q):
    s = q.strip().lower()
    if s.startswith("/model"):
        parts = q.split(None,1)
        global MODEL
        if len(parts)==2 and parts[1].strip():
            MODEL = parts[1].strip()
            return f"(model set to {MODEL})"
        else:
            return f"(current model {MODEL})"
    if s.startswith("/status"):
        return status_report()
    if s.startswith("/monitors") or "how many screen" in s or "how many monitor" in s:
        n = lt.count_monitors()
        return f"Monitors detected: {n}" if n>=0 else "(could not detect monitors)"
    if s.startswith("/windows") or "how many window" in s:
        n = lt.count_windows()
        return f"Visible top-level windows: {n}" if n>=0 else "(could not enumerate windows)"
    if s.startswith("/screenshot") or "screenshot" in s:
        path = lt.screenshot()
        return f"Screenshot saved: {path}"
    return None

def main():
    print('Brain chat ready. Type "exit" to quit.')
    print(f"(model={MODEL})")
    while True:
        try: q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower() == "exit": break

        # Local capabilities first
        local = handle_local(q)
        if local:
            append("assistant", local); print(local); continue

        # Planner + LLM
        append("user", q)
        try_planner(q)
        ans = llm_answer(q); append("assistant", ans); print(ans)
        extra = poll_tail(timeout=10, min_wait=1.0)
        if extra and extra.strip() and not extra.strip().startswith("echo:"):
            print(f"[ecosystem] {extra}")
    print("Bye.")

if __name__ == "__main__": main()
'@
Write-Ascii ".\dev\brain_chat_shell.py" $newShell

# --- restart background, route comms to brain, quick smoke ---
powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null
& $py dev\chatops_cli.py "Switch Comms to Brain (GPT) mode, disable echo, route bus 'comms/in' to Brain, write replies to reports\chat\exact_tail.jsonl" | Out-Null
& $py dev\core02_planner.py apply | Out-Null
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null

# Smoke: write a screenshot and counts
$smokePy = @'
from dev import local_tools as lt
print("monitors", lt.count_monitors())
print("windows", lt.count_windows())
print(lt.screenshot())
'@
Write-Ascii ".\dev\tools_smoke.py" $smokePy
$smoke = & $py -m dev.tools_smoke
Write-Ascii ".\reports\TOOLS_SMOKE.txt" $smoke

Write-Host "TOOLS_ENABLE complete."
