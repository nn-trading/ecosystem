param(
  [switch]$KeepRunning = $true,
  [int]$WaitSec = 25
)
Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
$ROOT = 'C:\bots\ecosys'
Set-Location -LiteralPath $ROOT

# --- dirs + dual config ---
@('dev','config','configs','reports','reports\chat','reports\screens','logs','runs','logs\archive','reports\archive\chat') | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
Set-Content -Encoding Ascii -LiteralPath config\model.yaml  -Value 'default: gpt-5`nlock: true'
Set-Content -Encoding Ascii -LiteralPath configs\model.yaml -Value 'default: gpt-5`nlock: true'
Set-Content -Encoding Ascii -LiteralPath config\comms.yaml  -Value 'mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl'
Set-Content -Encoding Ascii -LiteralPath configs\comms.yaml -Value 'mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl'
if (!(Test-Path reports\chat\exact_tail.jsonl)) { New-Item -ItemType File -Force -Path reports\chat\exact_tail.jsonl | Out-Null }

# --- rotate logs/tail safely ---
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
if (Test-Path logs\start_stdout.log)  { Move-Item logs\start_stdout.log  ('logs\archive\start_stdout_{0}.log' -f $ts) -ErrorAction SilentlyContinue }
if (Test-Path logs\start_stderr.log)  { Move-Item logs\start_stderr.log  ('logs\archive\start_stderr_{0}.log' -f $ts) -ErrorAction SilentlyContinue }
if (Test-Path reports\chat\exact_tail.jsonl) { try { Move-Item reports\chat\exact_tail.jsonl ('reports\archive\chat\exact_tail_{0}.jsonl' -f $ts) -ErrorAction Stop } catch {} }
if (-not (Test-Path reports\chat\exact_tail.jsonl)) { New-Item -ItemType File -Force -Path reports\chat\exact_tail.jsonl | Out-Null }

# --- prefer venv python, ensure deps ---
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { try { py -3 -m venv .venv } catch { python -m venv .venv } ; $py = Join-Path $ROOT '.venv\Scripts\python.exe' }
& $py -m pip install -U pip | Out-Null
& $py -m pip install 'openai>=1,<2' fastapi uvicorn psutil requests pywin32 mss pillow screeninfo keyboard pyautogui | Out-Null

# --- write Python modules (ASCII) ---
$auto_utils = @'
import os, json
def unique_path(path):
    base, ext = os.path.splitext(path)
    c = 0; cand = path
    while os.path.exists(cand):
        c += 1
        cand = f"{base}_{c:03d}{ext}"
    return cand
def root_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
def desktop_dir():
    return os.path.join(os.path.expanduser("~"), "Desktop")
def read_api_key():
    p = os.path.join(root_dir(), "api_key.txt")
    if os.path.isfile(p):
        try:
            return open(p, "r", encoding="utf-8", errors="ignore").read().strip()
        except: pass
    return os.getenv("OPENAI_API_KEY")
def jsonl_append(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", errors="ignore") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")
'@
Set-Content -Encoding Ascii -LiteralPath dev\auto_utils.py -Value $auto_utils

$tail_utils = @'
import os, json, time
from datetime import datetime
def _root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TAIL   = os.path.join(_root(), "reports", "chat", "exact_tail.jsonl")
SHADOW = os.path.join(_root(), "reports", "chat", "exact_tail_shadow.jsonl")
def now():
    return datetime.utcnow().isoformat()
def append(role, text):
    line = {"ts": now(), "role": role, "text": str(text)}
    try:
        os.makedirs(os.path.dirname(TAIL), exist_ok=True)
        with open(TAIL, "a", encoding="utf-8", errors="ignore") as f:
            f.write(json.dumps(line, ensure_ascii=True) + "\n")
    except Exception:
        with open(SHADOW, "a", encoding="utf-8", errors="ignore") as f:
            f.write(json.dumps(line, ensure_ascii=True) + "\n")
'@
Set-Content -Encoding Ascii -LiteralPath dev\tail_utils.py -Value $tail_utils

$tool_server = @'
from fastapi import FastAPI
from pydantic import BaseModel
import os, time, json, ctypes
from screeninfo import get_monitors
import mss, mss.tools
from dev.auto_utils import unique_path, root_dir, desktop_dir

app = FastAPI()
ROOT = root_dir()

class WriteReq(BaseModel):
    text: str
    stem: str | None = None
class Result(BaseModel):
    ok: bool
    path: str | None = None
    extra: dict | None = None

@app.get("/ping")
def ping(): return {"ok": True}
@app.get("/monitors")
def monitors(): return {"monitors": len(get_monitors())}

def _count_windows():
    user32 = ctypes.windll.user32
    IsWindowVisible = user32.IsWindowVisible
    titles = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                t = buf.value.strip()
                if t:
                    titles.append(t)
        return True
    user32.EnumWindows(enum_proc, 0)
    return len(titles)

@app.get("/windows")
def windows(): return {"windows": _count_windows()}

@app.post("/write")
def write(req: WriteReq):
    stem = req.stem or "auto_note"
    desk = desktop_dir()
    os.makedirs(desk, exist_ok=True)
    path = unique_path(os.path.join(desk, f"{stem}.txt"))
    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(req.text)
    return Result(ok=True, path=path)

@app.post("/screenshot")
def screenshot():
    outdir = os.path.join(ROOT, "reports", "screens")
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, f"screen_{int(time.time())}.png")
    path = unique_path(base)
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[0])
        mss.tools.to_png(shot.rgb, shot.size, output=path)
    return Result(ok=True, path=path)
'@
Set-Content -Encoding Ascii -LiteralPath dev\tool_server.py -Value $tool_server

$dispatcher = @'
import os, json, time, threading, requests
from dev.tail_utils import append, TAIL, SHADOW
from dev.auto_utils import root_dir

PORT = int(os.getenv("TOOL_SERVER_PORT", "8766"))
TOOL = f"http://127.0.0.1:{PORT}"

def handle_call(call):
    tool = call.get("tool")
    args = call.get("args", {}) or {}
    try:
        if tool == "write":
            r = requests.post(f"{TOOL}/write", json={"text": args.get("text",""), "stem": args.get("stem")})
            return r.json()
        if tool == "screenshot":
            r = requests.post(f"{TOOL}/screenshot")
            return r.json()
        if tool == "monitors":
            r = requests.get(f"{TOOL}/monitors")
            return r.json()
        if tool == "windows":
            r = requests.get(f"{TOOL}/windows")
            return r.json()
        return {"ok": False, "error": "unknown_tool"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def tail_iter(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2); continue
            yield line

def main():
    events_path = os.path.join(root_dir(), "reports", "DISPATCH_EVENTS.jsonl")
    os.makedirs(os.path.dirname(events_path), exist_ok=True)
    for raw in tail_iter(TAIL):
        try:
            obj = json.loads(raw)
        except:
            continue
        text = (obj.get("text") or "").strip()
        if obj.get("role") == "assistant" and text.startswith("[ecosystem-call]"):
            try:
                payload = text.split("] ", 1)[1]
                call = json.loads(payload)
            except:
                continue
            res = handle_call(call)
            append("assistant", "[ecosystem-result] " + json.dumps(res, ensure_ascii=True))
            with open(events_path, "a", encoding="utf-8", errors="ignore") as ef:
                ef.write(json.dumps({"call": call, "result": res}) + "\n")

if __name__ == "__main__":
    main()
'@
Set-Content -Encoding Ascii -LiteralPath dev\dispatcher.py -Value $dispatcher

$nl_router = @'
import os, json, time
from dev.tail_utils import append, TAIL
from dev.auto_utils import read_api_key, root_dir
from openai import OpenAI

MODEL = "gpt-5"
client = OpenAI(api_key=read_api_key())

SYS = (
    "You are a router. Output ONLY JSON: "
    '{"tool":"write|screenshot|monitors|windows","args":{...}}. '
    "Choose: if user asks to write/save/note -> write(text=...), "
    "if screenshot -> screenshot, if monitors/windows -> respective tool. "
    "When ambiguous, default to write with a short neutral note."
)

def tail_iter(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        # start near end
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2); continue
            yield line

def decide(user_text: str):
    msg = [
        {"role":"system","content":SYS},
        {"role":"user","content":user_text[:400]}
    ]
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=msg,
            temperature=0,
            max_completion_tokens=128
        )
        c = (r.choices[0].message.content or "").strip()
        return json.loads(c)
    except Exception:
        return {"tool":"write","args":{"text":f"Note: {user_text[:200]}" }}

def main():
    for raw in tail_iter(TAIL):
        try:
            obj = json.loads(raw)
        except:
            continue
        if obj.get("role") == "user":
            txt = (obj.get("text") or "").strip()
            call = decide(txt)
            append("assistant", "[ecosystem-call] " + json.dumps(call, ensure_ascii=True))

if __name__ == "__main__":
    main()
'@
Set-Content -Encoding Ascii -LiteralPath dev\nl_router.py -Value $nl_router

$inject = @'
import sys, json, time, os
from dev.tail_utils import append
txt = " ".join(sys.argv[1:]).strip() or "write a short note saying autonomous ok"
append("user", txt)
print("injected")
'@
Set-Content -Encoding Ascii -LiteralPath dev\tail_inject.py -Value $inject

# --- stop any previous helper PIDs ---
$pidsPath = 'reports\AUTONOMOUS_PIDS.json'
if (Test-Path $pidsPath) {
  try {
    $p = Get-Content $pidsPath | ConvertFrom-Json -ErrorAction SilentlyContinue
    foreach ($k in 'tool','dispatch','router') {
      $pid = [int]($p.$k)
      if ($pid -gt 0) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
    }
  } catch {}
}

# --- launch tool server + dispatcher + router (hidden) ---
$env:TOOL_SERVER_PORT = '8766'
$toolP = Start-Process -PassThru -WindowStyle Hidden $py -ArgumentList '-m','uvicorn','dev.tool_server:app','--host','127.0.0.1','--port',$env:TOOL_SERVER_PORT
$dispP = Start-Process -PassThru -WindowStyle Hidden $py -ArgumentList '-m','dev.dispatcher'
$routeP= Start-Process -PassThru -WindowStyle Hidden $py -ArgumentList '-m','dev.nl_router'
@{tool=$toolP.Id; dispatch=$dispP.Id; router=$routeP.Id} | ConvertTo-Json | Set-Content -Encoding Ascii $pidsPath

# --- wait for readiness ---
$ready = $false
for ($i=0; $i -lt 20; $i++) {
  try { $pong = (Invoke-WebRequest -Uri "http://127.0.0.1:$($env:TOOL_SERVER_PORT)/ping" -UseBasicParsing -TimeoutSec 2).Content; if ($pong -match '"ok":true') { $ready = $true; break } } catch {}
  Start-Sleep -Milliseconds 300
}
Start-Sleep -Milliseconds 500

# --- seed one user line and wait for result ---
& $py -m dev.tail_inject 'count my monitors and save a short note'
$deadline = (Get-Date).AddSeconds($WaitSec)
$got = $false
while ((Get-Date) -lt $deadline) {
  if (Select-String -Path 'reports\chat\exact_tail.jsonl','reports\\chat\\exact_tail_shadow.jsonl' -Pattern '[ecosystem-result]' -SimpleMatch) { $got = $true; break }
  if (Test-Path 'reports\DISPATCH_EVENTS.jsonl') { if (Select-String -Path 'reports\DISPATCH_EVENTS.jsonl' -Pattern '"result"' -SimpleMatch) { $got = $true; break } }
  Start-Sleep -Milliseconds 300
}

# --- summary + optional stop ---
$ok = $got
$sum = @()
$sum += ('CORE01 {0}' -f (Get-Date -Format s))
$sum += ('tool_server_pid={0}' -f $toolP.Id)
$sum += ('dispatcher_pid={0}' -f $dispP.Id)
$sum += ('router_pid={0}' -f $routeP.Id)
$sum += ('tail_has_result={0}' -f $ok)
Set-Content -Encoding Ascii -LiteralPath reports\CORE01_SUMMARY.txt -Value ($sum -join "`r`n")

if (-not $KeepRunning) {
  foreach ($pid in @($toolP.Id,$dispP.Id,$routeP.Id)) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
}
Write-Host ('=== CORE-01 COMPLETE === tail_has_result={0} keep_running={1}' -f $ok,$KeepRunning)
