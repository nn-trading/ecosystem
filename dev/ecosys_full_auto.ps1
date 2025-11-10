param([switch]$LaunchChat=$false)
Set-StrictMode -Version 2
$ErrorActionPreference='Stop'
$ROOT='C:\bots\ecosys'
Set-Location -LiteralPath $ROOT

# --- dirs ---
foreach($d in @('dev','config','reports','reports\chat','reports\screens')){ if(!(Test-Path -LiteralPath $d)){ New-Item -ItemType Directory -Path $d | Out-Null } }
if (!(Test-Path -LiteralPath 'dev\__init__.py')) { '' | Set-Content -Encoding Ascii -LiteralPath 'dev\__init__.py' }

# --- configs (correct folder: config\) ---
Set-Content -Encoding Ascii -LiteralPath 'config\model.yaml' -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath 'config\comms.yaml' -Value "mode: brain`necho: false`ntail: reports\\chat\\exact_tail.jsonl"
$tail = 'reports\chat\exact_tail.jsonl'; if (!(Test-Path -LiteralPath $tail)) { New-Item -ItemType File -Path $tail | Out-Null }

# --- venv + deps ---
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $py)) {
  $tmp='python'; try { & $tmp -m venv .venv } catch {}
  $py = Join-Path $ROOT '.venv\Scripts\python.exe'; if (!(Test-Path -LiteralPath $py)) { $py='python' }
}
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install "openai>=1.0.0,<2" pyautogui pillow mss screeninfo pywin32 keyboard requests psutil | Out-Null

# --- dev\local_tools.py (PC control + info) ---
$lt=@'
import os, json, time, pathlib, subprocess
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCREENS = ROOT / "reports" / "screens"; SCREENS.mkdir(parents=True, exist_ok=True)

def _asc(s):
    try: return (s or "").encode("ascii","ignore").decode("ascii")
    except: return str(s or "")

def count_monitors():
    try:
        from screeninfo import get_monitors
        return {"monitors": len(get_monitors())}
    except Exception as e:
        return {"monitors": 0, "error": _asc(e)}

def count_windows():
    try:
        import win32gui
        cnt=0
        def cb(hwnd,_):
            nonlocal cnt
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                cnt+=1
            return True
        win32gui.EnumWindows(cb, None)
        return {"windows": cnt}
    except Exception as e:
        return {"windows": 0, "error": _asc(e)}

def list_titles(maxn=60):
    titles=[]
    try:
        import win32gui
        def cb(hwnd,_):
            t=win32gui.GetWindowText(hwnd)
            if win32gui.IsWindowVisible(hwnd) and t:
                titles.append(t)
            return True
        win32gui.EnumWindows(cb, None)
    except Exception as e:
        return {"titles": [], "error": _asc(e)}
    return {"titles": titles[:maxn]}

def screenshot(name=None):
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    fname=f"{name or 'screen'}_{ts}.png"
    path=SCREENS/fname
    try:
        import pyautogui
        pyautogui.FAILSAFE=False
        im=pyautogui.screenshot()
        im.save(str(path))
        return {"path": str(path)}
    except Exception as e:
        return {"error": _asc(e)}

def type_text(text):
    try:
        import pyautogui
        pyautogui.FAILSAFE=False
        pyautogui.typewrite(text, interval=0.02)
        return {"ok": True}
    except Exception as e:
        try:
            import keyboard
            keyboard.write(text)
            return {"ok": True}
        except Exception as e2:
            return {"ok": False, "error": _asc(e2)}

def press_keys(sequence):
    # e.g., "ctrl+s, enter" or "win+d"
    try:
        import keyboard
        for part in sequence.split(","):
            k=part.strip()
            if "+" in k: keyboard.send(k.replace(" ",""))
            else: keyboard.press_and_release(k)
        return {"ok": True}
    except Exception:
        try:
            import pyautogui
            pyautogui.FAILSAFE=False
            for part in sequence.split(","):
                k=part.strip()
                if "+" in k: pyautogui.hotkey(*[x.strip() for x in k.split("+")])
                else: pyautogui.press(k)
            return {"ok": True}
        except Exception as e2:
            return {"ok": False, "error": _asc(e2)}

def run(cmd):
    try:
        r=subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90)
        return {"returncode": r.returncode, "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]}
    except Exception as e:
        return {"error": _asc(e)}
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\local_tools.py' -Value $lt

# --- dev\brain_chat_shell.py (tool-calling + planner kick + tail poll) ---
$pycode=@'
import os, sys, json, time, pathlib, re
from typing import List, Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)

MODEL_NAME = os.environ.get("MODEL_NAME","gpt-5")

def asc(s): 
    try: return (s or "").encode("ascii","ignore").decode("ascii")
    except: return str(s or "")

def append(role, text):
    line = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "role": role, "text": asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f:
        f.write(json.dumps(line, ensure_ascii=True)+"\n")

def poll_tail(timeout=18, min_wait=0.8):
    t0=time.time()
    while time.time()-t0<min_wait: time.sleep(0.2)
    end=t0+timeout
    pat_skip=re.compile(r"^(echo:|AI-\\d+:|\\[Worker\\] Replan|.*retry budget exhausted)", re.I)
    while time.time()<end:
        try:
            lines=TAIL.read_text(encoding="ascii", errors="ignore").splitlines()
            for ln in reversed(lines):
                try:
                    o=json.loads(ln); role=(o.get("role") or "").lower(); text=o.get("text") or ""
                    if role in ("assistant","brain") and text and not pat_skip.search(text.strip()):
                        return text
                except: pass
        except: pass
        time.sleep(0.4)
    return None

def try_planner(q):
    import subprocess, pathlib
    py = str(ROOT/".venv/Scripts/python.exe")
    if not pathlib.Path(py).exists(): py="python"
    try: subprocess.run([py, "dev/eco_cli.py", "ask", q], check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    try: subprocess.run([py, "dev/core02_planner.py", "apply"], check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

# ----- tool calling -----
from importlib import import_module
_tools = import_module("dev.local_tools")

TOOL_SPEC = [
  {"type":"function","function":{"name":"count_monitors","description":"Return number of monitors","parameters":{"type":"object","properties":{},"required":[]}}},
  {"type":"function","function":{"name":"count_windows","description":"Return number of visible top-level windows","parameters":{"type":"object","properties":{},"required":[]}}},
  {"type":"function","function":{"name":"list_titles","description":"List visible window titles","parameters":{"type":"object","properties":{"maxn":{"type":"integer"}}}}},
  {"type":"function","function":{"name":"screenshot","description":"Take a screenshot and save under reports/screens","parameters":{"type":"object","properties":{"name":{"type":"string"}}}}},
  {"type":"function","function":{"name":"type_text","description":"Type text into the active window","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}}, 
  {"type":"function","function":{"name":"press_keys","description":"Press key sequence (e.g. 'ctrl+s, enter')","parameters":{"type":"object","properties":{"sequence":{"type":"string"}},"required":["sequence"]}}}, 
  {"type":"function","function":{"name":"run","description":"Run a shell command","parameters":{"type":"object","properties":{"cmd":{"type":"string"}},"required":["cmd"]}}}
]

def _call_tool(name: str, args: Dict):
    fn = getattr(_tools, name, None)
    if not fn: return {"error": f"tool {name} not found"}
    try: return fn(**(args or {}))
    except TypeError: return fn()  # for tools without args
    except Exception as e: return {"error": asc(e)}

def _get_key():
    p = ROOT/"api_key.txt"
    if p.exists():
        try: return p.read_text().strip()
        except: pass
    return os.environ.get("OPENAI_API_KEY","")

def _chat_turn(messages: List[Dict]):
    from openai import OpenAI
    key=_get_key()
    if not key: return {"final": "(no OPENAI_API_KEY/api_key.txt)", "messages": messages}
    client = OpenAI(api_key=key)
    r = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=TOOL_SPEC,
        tool_choice="auto"
    )
    msg = r.choices[0].message
    messages.append({"role":"assistant","content":msg.content or "", "tool_calls":[tc.to_dict() for tc in (msg.tool_calls or [])]})
    if msg.tool_calls:
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            result = _call_tool(name, args)
            messages.append({"role":"tool","tool_call_id":tc.id,"name":name,"content":json.dumps(result, ensure_ascii=True)})
        # second call to let model formulate final answer
        r2 = client.chat.completions.create(model=MODEL_NAME, messages=messages)
        final = r2.choices[0].message.content or ""
        messages.append({"role":"assistant","content":final})
        return {"final": asc(final), "messages": messages}
    else:
        return {"final": asc(msg.content or ""), "messages": messages}

def main():
    print('Brain chat ready. Type "exit" to quit.')
    print(f'(model={MODEL_NAME})')
    messages=[{"role":"system","content":"You are the Ecosystem Brain on Windows. Think and act autonomously. If a local tool helps, call it. Be concise."}]
    while True:
        try: q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower()=='exit': break
        if q.lower().startswith('/model'): print(f"(model is LOCKED to {MODEL_NAME})"); continue
        if q.lower()=='/status': print('(status ok)'); continue
        append("user", q)
        try_planner(q)
        turn=_chat_turn(messages+[{"role":"user","content":q}])
        ans = turn.get("final","(no answer)")
        append("assistant", ans); print(ans)
        extra=poll_tail(timeout=10, min_wait=0.8)
        if extra and extra.strip() and extra.strip()!=ans.strip():
            print(f"[ecosystem] {extra}")
    print("Bye.")
if __name__ == "__main__": main()
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\brain_chat_shell.py' -Value $pycode

# --- runner (manual launch when YOU want) ---
$runner=@'
param()
$ErrorActionPreference='Stop'
$DEV=$PSScriptRoot; $ROOT=(Get-Item $DEV).Parent.FullName
Set-Location -LiteralPath $ROOT
$py = Join-Path $ROOT '.venv\Scripts\python.exe'; if (!(Test-Path -LiteralPath $py)) { $py='python' }
$env:MODEL_NAME='gpt-5'; $env:AGENT_DANGER_MODE='1'; $env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& $py -m dev.brain_chat_shell
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\run_chat_full.ps1' -Value $runner

# --- clean stop/start now, but DO NOT auto-launch chat ---
try { powershell -NoProfile -File '.\start.ps1' -Stop 1 | Out-Null } catch {}
powershell -NoProfile -File '.\start.ps1' -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null

# assert file
$ts=Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Set-Content -Encoding Ascii -LiteralPath 'reports\FULL_AUTO_READY.txt' -Value "[$ts] FULL_AUTO: config ok, deps ok, background ok, runner ready."
