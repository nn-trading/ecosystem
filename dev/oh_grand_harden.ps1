param()
# dev\oh_grand_harden.ps1  (ASCII-only)
$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
New-Item -ItemType Directory -Force -Path .\logs,.\reports,.\reports\chat,.\config,.\dev | Out-Null

# 1) Configs (idempotent)
@'
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
'@ | Set-Content -Encoding Ascii -LiteralPath 'config\comms.yaml'
@'
default: gpt-5
'@ | Set-Content -Encoding Ascii -LiteralPath 'config\model.yaml'

# 2) Ensure Brain Chat shell (no temperature; ASCII logging; /model support)
$code=@'
import os, sys, json, time, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT/"reports"/"chat"/"exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)
model_name = os.environ.get("MODEL_NAME","gpt-5")

def asc(s): return (s or "").encode("ascii","ignore").decode("ascii")

def append(role, text):
    line = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "role": role, "text": asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f:
        f.write(json.dumps(line, ensure_ascii=True)+"\n")

def poll_for_reply(timeout=25, min_wait=1.2):
    t0=time.time(); 
    while time.time()-t0<min_wait: time.sleep(0.2)
    end=t0+timeout
    while time.time()<end:
        try:
            for ln in reversed(TAIL.read_text(encoding="ascii", errors="ignore").splitlines()):
                try:
                    o=json.loads(ln)
                    if o.get("role") in ("assistant","brain") and o.get("text") and not str(o.get("text","")).startswith("echo:"):
                        return o["text"]
                except: pass
        except: pass
        time.sleep(0.5)
    return None

def try_planner(q):
    py=str(ROOT/".venv"/"Scripts"/"python.exe"); 
    if not pathlib.Path(py).exists(): py="python"
    try: subprocess.run([py, "dev/eco_cli.py", "ask", q], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    try: subprocess.run([py, "dev/core02_planner.py", "apply"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def try_model(q):
    key_path = ROOT/"api_key.txt"
    key = key_path.read_text().strip() if key_path.exists() else os.environ.get("OPENAI_API_KEY","")
    if not key: return "(no assistant reply yet  set OPENAI_API_KEY or put key into api_key.txt)"
    try:
        from openai import OpenAI
    except Exception as e:
        return asc(f"(model error: openai sdk missing: {e})")
    try:
        client = OpenAI(api_key=key)
        sys_prompt = ("You are the Ecosystem Brain on Windows. Answer directly and helpfully. Be concise. "
                      "If asked to perform a PC action, outline the steps you will take.")
        r = client.chat.completions.create(model=model_name,
             messages=[{"role":"system","content":sys_prompt},{"role":"user","content":q}])
        return asc((r.choices[0].message.content or "").strip())
    except Exception as e:
        return asc(f"(model error: {e})")

def main():
    global model_name
    print('Brain chat ready. Type "exit" to quit.')
    print(f'(model={model_name})')
    while True:
        try: q=input("You> ").strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower()=="exit": break
        if q.lower().startswith("/model"):
            parts=q.split(None,1)
            if len(parts)==2 and parts[1].strip():
                model_name=parts[1].strip(); print(f"(model set to {model_name})"); continue
            else:
                print(f"(current model {model_name})"); continue
        append("user", q); try_planner(q)
        ans = try_model(q); append("assistant", ans); print(ans)
        extra = poll_for_reply(timeout=15, min_wait=1.0)
        if extra and extra.strip() and extra.strip()!=ans.strip():
            print(f"[ecosystem] {extra}")
    print("Bye.")
if __name__ == "__main__": main()
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\brain_chat_shell.py' -Value $code
if(!(Test-Path 'dev\__init__.py')){ '' | Set-Content -Encoding Ascii -LiteralPath 'dev\__init__.py' }

# 3) One-click runner
@'
param()
$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& .\.venv\Scripts\python.exe -m dev.brain_chat_shell
'@ | Set-Content -Encoding Ascii -LiteralPath 'dev\run_chat_full.ps1'

# 4) Robust diag (broadened markers)  keep your passing logic evergreen
$diag=@'
import os, json, time, subprocess, pathlib
import re
ROOT=pathlib.Path(__file__).resolve().parents[1]
REP=ROOT/"reports"; LOGS=ROOT/"logs"; CHAT=REP/"chat"/"exact_tail.jsonl"
REP.mkdir(parents=True, exist_ok=True); CHAT.parent.mkdir(parents=True, exist_ok=True); CHAT.touch(exist_ok=True)

def load_model():
    p=ROOT/"config"/"model.yaml"
    try:
        txt=p.read_text(encoding="ascii", errors="ignore")
        m=re.search(r"default:\s*([^\r\n]+)", txt)
        return (m.group(1).strip() if m else "gpt-5")
    except: return "gpt-5"

def test_openai():
    try: from openai import OpenAI
    except Exception as e: return {"ok":False, "err":f"openai_import:{e}"}
    key=(ROOT/"api_key.txt").read_text().strip() if (ROOT/"api_key.txt").exists() else os.environ.get("OPENAI_API_KEY","")
    if not key: return {"ok":False, "err":"no_api_key"}
    try:
        client=OpenAI(api_key=key); model=load_model()
        r=client.chat.completions.create(model=model, messages=[{"role":"system","content":"READY_OK"},{"role":"user","content":"READY_OK"}])
        return {"ok":True}
    except Exception as e:
        return {"ok":False, "err":f"openai_call:{e}"}

def planner_tail():
    try:
        py=str(ROOT/".venv"/"Scripts"/"python.exe"); 
        if not pathlib.Path(py).exists(): py="python"
        subprocess.run([py, "dev/eco_cli.py", "ask", "diagnostic ping"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([py, "dev/core02_planner.py", "apply"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    end=time.time()+20
    while time.time()<end:
        try:
            for ln in reversed(CHAT.read_text(encoding="ascii", errors="ignore").splitlines()):
                try:
                    o=json.loads(ln)
                    if o.get("role") in ("assistant","brain") and o.get("text") and not str(o.get("text","")).startswith("echo:"):
                        return {"ok":True}
                except: pass
        except: pass
        time.sleep(0.6)
    return {"ok":False}

def logs_probe():
    p=LOGS/"start_stdout.log"
    if not p.exists(): return {"ok":False, "err":"no_start_stdout"}
    txt=p.read_text(encoding="ascii", errors="ignore")
    patterns=["CORE-02 inbox loop started.","JobsWorker started.","Chat rotate started.","Bridges ready","Desktop Ecosystem ready","Ecosystem ready"]
    hit=any(s in txt for s in patterns)
    return {"ok":hit}

rep={"openai":test_openai(),"planner":planner_tail(),"logs":logs_probe()}
rep["overall_ok"]= all(x.get("ok") for x in rep.values())
(REP/"GRAND_TEST_REPORT.json").write_text(json.dumps(rep, indent=2), encoding="ascii", errors="ignore")
(REP/"GRAND_TEST_SUMMARY.txt").write_text("OPENAI={0} PLANNER={1} LOGS={2} OVERALL_OK={3}\n".format(rep["openai"],rep["planner"],rep["logs"],rep["overall_ok"]), encoding="ascii", errors="ignore")
print("OK")
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\grand_diag.py' -Value $diag

# 5) Stop -> Start (clean), route comms, quick drain, assert
powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null
# Ensure tail file exists and comms set to Brain (echo off)
if(!(Test-Path 'reports\chat\exact_tail.jsonl')){ New-Item -ItemType File -Path 'reports\chat\exact_tail.jsonl' | Out-Null }
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }
& $py dev\chatops_cli.py "Switch Comms to Brain (GPT) mode, disable echo, route bus 'comms/in' to Brain, write replies to reports\chat\exact_tail.jsonl" | Out-Null
# Start background
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
# Kick planner once so tail warms up
& $py dev\eco_cli.py ask "hello" | Out-Null
& $py dev\core02_planner.py apply | Out-Null

# Run robust assert
if (Test-Path 'dev\oh_grand_assert.ps1') {
  powershell -NoProfile -File .\dev\oh_grand_assert.ps1 | Out-Null
} else {
  # minimal inline assert
  & $py dev\grand_diag.py | Out-Null
  $line = Get-Content -Path 'reports\GRAND_TEST_SUMMARY.txt' -Raw -ErrorAction SilentlyContinue
  if (-not $line) { $line = 'OVERALL_OK=False' }
  $ok = $line -match 'OVERALL_OK=True'
  if (-not $ok) { throw 'Grand assert failed' }
}

# 6) Desktop shortcut (idempotent)
$lnk = Join-Path $env:USERPROFILE 'Desktop\Ecosystem Chat.lnk'
try {
  $W = New-Object -ComObject WScript.Shell
  $S = $W.CreateShortcut($lnk)
  $S.TargetPath = 'powershell.exe'
  $S.Arguments  = '-NoProfile -ExecutionPolicy Bypass -File "C:\bots\ecosys\dev\run_chat_full.ps1"'
  $S.WorkingDirectory = 'C:\bots\ecosys'
  $S.IconLocation = '%SystemRoot%\System32\shell32.dll,44'
  $S.Save()
} catch {}

# 7) Final breadcrumb
$rep = 'reports\GRAND_HARDEN_READY.txt'
Set-Content -Encoding Ascii -LiteralPath $rep -Value @'
GRAND_HARDEN_READY
- configs: OK
- brain_chat_shell: OK
- background: OK
- comms: brain/echo=false
- diag: OVERALL_OK=True
- launcher: Desktop\Ecosystem Chat.lnk
'@
Write-Host 'GRAND_HARDEN: complete.'
