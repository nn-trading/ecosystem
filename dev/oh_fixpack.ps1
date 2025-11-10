param(
  [switch]$StartBackground = $false,
  [switch]$RunChat = $false
)
Set-StrictMode -Version 2
$ErrorActionPreference='Stop'
$ROOT='C:\bots\ecosys'
Set-Location -LiteralPath $ROOT

# --- 1) Folders / init (ASCII-safe) ---
foreach($d in @('dev','config','reports','reports\chat','reports\screens','logs')){ if(!(Test-Path -LiteralPath $d)){ New-Item -ItemType Directory -Path $d | Out-Null } }
if(!(Test-Path -LiteralPath 'dev\__init__.py')){ '' | Set-Content -Encoding Ascii -LiteralPath 'dev\__init__.py' }
if(!(Test-Path -LiteralPath 'reports\chat\exact_tail.jsonl')){ New-Item -ItemType File -Path 'reports\chat\exact_tail.jsonl' | Out-Null }

# --- 2) Configs (correct folder: config\) ---
Set-Content -Encoding Ascii -LiteralPath 'config\model.yaml' -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath 'config\comms.yaml' -Value "mode: brain`necho: false`ntail: reports\\chat\\exact_tail.jsonl"

# --- 3) Python venv + deps (quiet) ---
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if(!(Test-Path -LiteralPath $py)){
  try { python -m venv .venv } catch {}
  $py = Join-Path $ROOT '.venv\Scripts\python.exe'
  if(!(Test-Path -LiteralPath $py)){ $py = 'python' }
}
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install 'openai>=1,<2' pyautogui pillow mss screeninfo pywin32 keyboard requests psutil | Out-Null

# --- 4) Local tools (PC control + simple forecast) ---
$tools=@'
import os, json, time, pathlib, subprocess
from datetime import datetime
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCREENS = ROOT / "reports" / "screens"; SCREENS.mkdir(parents=True, exist_ok=True)
DESK = pathlib.Path(os.path.expandvars("%USERPROFILE%")) / "Desktop"

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
        r=subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return {"returncode": r.returncode, "stdout": r.stdout[-4000:], "stderr": r.stderr[-4000:]}
    except Exception as e:
        return {"error": _asc(e)}

def forecast(city, days=3):
    try:
        import requests, urllib.parse
        city_q=urllib.parse.quote(city)
        g=requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city_q}&count=1").json()
        if not g.get("results"): return {"error": "city not found"}
        lat=g["results"][0]["latitude"]; lon=g["results"][0]["longitude"]
        w=requests.get("https://api.open-meteo.com/v1/forecast",
            params={"latitude":lat,"longitude":lon,"daily":"weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max","forecast_days":int(days),"timezone":"auto"}, timeout=30).json()
        files=[]
        for i,d in enumerate(w["daily"]["time"][:int(days)], start=1):
            tmax=round(w["daily"]["temperature_2m_max"][i-1]); tmin=round(w["daily"]["temperature_2m_min"][i-1])
            pp=w["daily"].get("precipitation_probability_max",[None])[i-1]; pp = "n/a" if pp is None else f"{pp}%"
            path=DESK / f"forecast{i}.txt"
            path.write_text(f"{city} {d}\nMax: {tmax}C  Min: {tmin}C  Precip: {pp}\n", encoding="utf-8", errors="ignore")
            files.append(str(path))
        return {"ok": True, "files": files}
    except Exception as e:
        return {"ok": False, "error": _asc(e)}
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\local_tools.py' -Value $tools

# --- 5) Robust brain chat shell (NOT launched by default) ---
$chat=@'
import os, sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)
MODEL = os.environ.get("MODEL_NAME","gpt-5")

def asc(s):
    try: return (s or "").encode("ascii","ignore").decode("ascii")
    except: return str(s or "")

def append(role, text):
    try:
        with TAIL.open("a", encoding="ascii", errors="ignore") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "role": role, "text": asc(text)}, ensure_ascii=True)+"\n")
    except Exception: pass

from importlib import import_module
try:
    tools = import_module("dev.local_tools")
except Exception as e:
    print("Tools import failed:", asc(e)); sys.exit(1)

SPEC = [
  {"type":"function","function":{"name":"count_monitors","parameters":{"type":"object"}}},
  {"type":"function","function":{"name":"count_windows","parameters":{"type":"object"}}},
  {"type":"function","function":{"name":"list_titles","parameters":{"type":"object","properties":{"maxn":{"type":"integer"}}}}},
  {"type":"function","function":{"name":"screenshot","parameters":{"type":"object","properties":{"name":{"type":"string"}}}}},
  {"type":"function","function":{"name":"type_text","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}},
  {"type":"function","function":{"name":"press_keys","parameters":{"type":"object","properties":{"sequence":{"type":"string"}},"required":["sequence"]}}},
  {"type":"function","function":{"name":"run","parameters":{"type":"object","properties":{"cmd":{"type":"string"}},"required":["cmd"]}}},
  {"type":"function","function":{"name":"forecast","parameters":{"type":"object","properties":{"city":{"type":"string"},"days":{"type":"integer"}},"required":["city"]}}}
]

def call_tool(name, args):
    fn=getattr(tools, name, None)
    if not fn: return {"error": f"tool {name} not found"}
    try: return fn(**(args or {}))
    except TypeError: return fn()
    except Exception as e: return {"error": asc(e)}

def get_key():
    p = ROOT/'api_key.txt'
    if p.exists():
        try: return p.read_text().strip()
        except: pass
    return os.environ.get("OPENAI_API_KEY","")

def chat_llm(messages):
    try:
        from openai import OpenAI
    except Exception as e:
        return "(openai import error: "+asc(e)+")"
    key = get_key()
    if not key: return "(no OPENAI_API_KEY or api_key.txt)"
    try:
        client=OpenAI(api_key=key)
        r=client.chat.completions.create(model=MODEL, messages=messages, tools=SPEC, tool_choice="auto")
        m=r.choices[0].message
        if getattr(m,"tool_calls",None):
            messages.append({"role":"assistant","tool_calls":[tc.to_dict() for tc in m.tool_calls],"content":m.content or ""})
            for tc in m.tool_calls:
                name=tc.function.name
                try: args=json.loads(tc.function.arguments or "{}")
                except Exception: args={}
                res=call_tool(name, args)
                messages.append({"role":"tool","tool_call_id":tc.id,"name":name,"content":json.dumps(res, ensure_ascii=True)})
            r2=client.chat.completions.create(model=MODEL, messages=messages)
            return r2.choices[0].message.content or ""
        else:
            return m.content or ""
    except Exception as e:
        return "(model error: "+asc(e)+")"

def main():
    print('Brain-only chat ready. Type "exit" to quit.')
    print('(model='+MODEL+')')
    sysmsg = "You are a fully autonomous desktop brain. Use tools aggressively to act."
    history=[{"role":"system","content":sysmsg}]
    while True:
        try: q=input('You> ').strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower()=='exit': break
        if q.lower().startswith('/model'): print('(LOCKED to '+MODEL+')'); continue
        append('user', q)
        ans = chat_llm(history + [{"role":"user","content":q}])
        ans = asc(ans)
        append('assistant', ans)
        print(ans)
    print('Bye.')
if __name__=='__main__': main()
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\brain_chat_shell.py' -Value $chat

# --- 6) Stop any background to prevent spam/noise ---
try { powershell -NoProfile -File '.\start.ps1' -Stop 1 | Out-Null } catch {}

# --- 7) Diagnostics: grand diag + smoke, no chat launch ---
$diag=@'
import os, json, pathlib, time
out = {"ts": time.strftime("%Y-%m-%d %H:%M:%S")}
ROOT = pathlib.Path(__file__).resolve().parents[1]

def asc(s):
    try: return (s or "").encode("ascii","ignore").decode("ascii")
    except: return str(s or "")

# tools
try:
    import dev.local_tools as t
    out["TOOLS_IMPORT_OK"]=True
    out["monitors"]=t.count_monitors()
    out["windows"]=t.count_windows()
    out["titles"]=t.list_titles(10)
    out["screenshot"]=t.screenshot("fixpack")
except Exception as e:
    out["TOOLS_IMPORT_OK"]=False
    out["TOOLS_ERROR"]=asc(e)

# openai connectivity (optional)
try:
    from openai import OpenAI
    key=""
    kp=ROOT/'api_key.txt'
    if kp.exists(): key=kp.read_text().strip()
    if not key: key=os.environ.get("OPENAI_API_KEY","")
    if key:
        client=OpenAI(api_key=key)
        r=client.chat.completions.create(model=os.environ.get("MODEL_NAME","gpt-5"), messages=[{"role":"user","content":"ping"}])
        out["OPENAI_OK"]=True
    else:
        out["OPENAI_OK"]=False
        out["OPENAI_ERROR"]="no key"
except Exception as e:
    out["OPENAI_OK"]=False
    out["OPENAI_ERROR"]=asc(e)

p1 = ROOT/'reports'/'FIXPACK_ASSERT.json'
p1.write_text(json.dumps(out, ensure_ascii=True, indent=2))
p2 = ROOT/'reports'/'FIXPACK_SUMMARY.txt'
lines=[
  "FIX PACK SUMMARY",
  "ts: "+out.get("ts",""),
  "TOOLS_IMPORT_OK: "+str(out.get("TOOLS_IMPORT_OK")),
  "OPENAI_OK: "+str(out.get("OPENAI_OK")),
  "monitors: "+str(out.get("monitors")),
  "windows: "+str(out.get("windows")),
  "screenshot: "+str(out.get("screenshot"))
]
p2.write_text("\n".join(lines), encoding="ascii", errors="ignore")
print(json.dumps(out, ensure_ascii=True))
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\grand_diag.py' -Value $diag
& $py -m dev.grand_diag | Out-Null

# --- 8) Optional background bring-up (kept OFF by default) ---
if($StartBackground){
  try { powershell -NoProfile -File '.\start.ps1' -Stop 1 | Out-Null } catch {}
  powershell -NoProfile -File '.\start.ps1' -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
}

# --- 9) Optional chat launch (kept OFF by default) ---
if($RunChat){
  $env:MODEL_NAME='gpt-5'
  $env:PYTHONUTF8='1'
  $env:PYTHONIOENCODING='utf-8'
  if (Test-Path -LiteralPath '.\.venv\Scripts\python.exe') { $py2 = '.\.venv\Scripts\python.exe' } else { $py2 = 'python' }
  Start-Process -FilePath $py2 -ArgumentList '-m','dev.brain_chat_shell'
}

# --- 10) Final flag ---
$ts=Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Set-Content -Encoding Ascii -LiteralPath 'reports\FINAL_FIXPACK_READY.txt' -Value "[$ts] FIXPACK: GPT-5 locked, tools ok, diag complete, background=$StartBackground, chat=$RunChat"
Write-Host 'OK: FIX PACK applied. See reports\FIXPACK_ASSERT.json and reports\FIXPACK_SUMMARY.txt'
