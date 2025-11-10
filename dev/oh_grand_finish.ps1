param()
$ErrorActionPreference = "Stop"

function Write-Ascii([string]$Path, [string]$Text){
  $d = Split-Path -Parent $Path; if ($d) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
  [IO.File]::WriteAllText($Path, $Text, [Text.Encoding]::ASCII)
}

# Paths / python
$root = "C:\bots\ecosys\"
$py = ".\.venv\Scripts\python.exe"; if (-not (Test-Path $py)) { $py = "python" }

# 1) Stop background and do a quick vacuum pass safely
try { powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null } catch {}
if (Test-Path '.\maintain.ps1') {
  try { powershell -NoProfile -File .\maintain.ps1 -VacuumDbs 1 | Out-Null } catch {}
}

# 2) Ensure chat configs (no echo; brain mode; tail path)
New-Item -ItemType Directory -Force -Path .\config, .\reports\chat | Out-Null
Write-Ascii 'config\comms.yaml' @"
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
"@
Write-Ascii 'config\model.yaml' @"
default: gpt-5
"@

# 3) Install/refresh Brain Chat shell (ASCII-only, immediate LLM + planner)
$brain = @'
import os, sys, json, time, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)

model_name = os.environ.get("MODEL_NAME","gpt-5")
def asc(s): return (s or "").encode("ascii","ignore").decode("ascii")
def append(role, text):
    line = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "role": role, "text": asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f: f.write(json.dumps(line, ensure_ascii=True)+"\n")

def try_planner(q):
    py = str(ROOT/".venv"/"Scripts"/"python.exe"); 
    if not pathlib.Path(py).exists(): py = "python"
    try: subprocess.run([py, "dev/eco_cli.py", "ask", q], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    try: subprocess.run([py, "dev/core02_planner.py", "apply"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def try_model(q):
    key_path = ROOT/"api_key.txt"
    key = key_path.read_text().strip() if key_path.exists() else os.environ.get("OPENAI_API_KEY","")

    if not key: 
        return "(no assistant reply yet  put key into api_key.txt)"
    try:
        from openai import OpenAI
    except Exception as e:
        return asc(f"(model error: openai sdk missing: {e})")
    try:
        client = OpenAI(api_key=key)
        sys_prompt = (
            "You are the Ecosystem Brain running on Windows. "
            "Answer the user directly and helpfully. Do not ask them for goals. "
            "Be concise. If they ask for a PC action, briefly describe the steps you will take."
        )
        r = client.chat.completions.create(
            model=model_name,
            messages=[{"role":"system","content":sys_prompt},{"role":"user","content":q}]
        )
        return asc((r.choices[0].message.content or "").strip())
    except Exception as e:
        return asc(f"(model error: {e})")

def main():
    global model_name
    print('Brain chat ready. Type "exit" to quit.')
    print(f'(model={model_name})')
    while True:
        try: q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower() == "exit": break
        if q.lower().startswith("/model"):
            parts = q.split(None,1)
            if len(parts)==2 and parts[1].strip():
                model_name = parts[1].strip(); print(f"(model set to {model_name})"); continue
            else:
                print(f"(current model {model_name})"); continue
        append("user", q); 
        try_planner(q)                  # kick Ecosystem planner
        ans = try_model(q)              # immediate reply
        append("assistant", ans); print(ans)
    print("Bye.")
if __name__ == "__main__": 
    # ensure package importability
    (ROOT/"dev"/"__init__.py").touch()
    main()
'@
Write-Ascii 'dev\brain_chat_shell.py' $brain
if (-not (Test-Path 'dev\__init__.py')) { Write-Ascii 'dev\__init__.py' '' }

# 4) One-click runner that boots background then launches chat
$runner = @'
param()
$ErrorActionPreference = "Stop"
$py = ".\\.venv\\Scripts\\python.exe"; if (-not (Test-Path $py)) { $py = "python" }
# Start background (no heavy maintenance)
powershell -NoProfile -File .\\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& $py -m dev.brain_chat_shell
'@
Write-Ascii 'dev\run_chat_full.ps1' $runner

# 5) Route Comms->Brain; disable echo; apply plan; quick drain
try { & $py dev\chatops_cli.py "Switch Comms to Brain (GPT) mode, disable echo, route bus 'comms/in' to Brain, write replies to reports\chat\exact_tail.jsonl" | Out-Null } catch {}
try { & $py dev\core02_planner.py apply | Out-Null } catch {}
try { & $py -m dev.jobs_drain --loops 5 --interval 0.5 | Out-Null } catch {}

# 6) Start background cleanly
try { powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null } catch {}

# 7) Smoke: non-interactive chat (hello -> exit); capture last assistant line
$smoke = @'
import json, pathlib, time, subprocess, sys, os
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT/"reports"/"chat"/"exact_tail.jsonl"
py = str(ROOT/".venv"/"Scripts"/"python.exe")
if not pathlib.Path(py).exists(): py = "python"
cmd = [py, "-m", "dev.brain_chat_shell"]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    p.stdin.write("hello\nexit\n"); p.stdin.flush()
    out, err = p.communicate(timeout=20)
except Exception as e:
    out, err = "", f"timeout_or_err: {e}"

def tail_last():
    if not TAIL.exists(): return None
    lines = TAIL.read_text(encoding="ascii", errors="ignore").splitlines()
    for ln in reversed(lines):
        try:
            o=json.loads(ln)
            if o.get("role") in ("assistant","brain") and o.get("text") and not str(o.get("text",""))[:5]=="echo:":
                return o.get("text")
        except: pass
    return None
last = tail_last() or "(no assistant reply recorded)"
(pathlib.Path(ROOT/"reports"/"GRAND_READY.txt")).write_text(
    "SMOKE_OUT:\n"+ (out or "") +"\nLAST_ASSISTANT:\n"+last+"\n", encoding="ascii", errors="ignore")
print("OK")
'@
Write-Ascii 'dev\grand_smoke.py' $smoke
try { & $py dev\grand_smoke.py | Out-Null } catch {}

# 8) Desktop shortcut for one-click launch
try {
  $W = New-Object -ComObject WScript.Shell
  $lnk = Join-Path $env:USERPROFILE 'Desktop\Ecosystem Chat.lnk'
  $tsk = $W.CreateShortcut($lnk)
  $tsk.TargetPath = 'powershell.exe'
  $tsk.Arguments  = '-NoProfile -ExecutionPolicy Bypass -File "C:\bots\ecosys\dev\run_chat_full.ps1"'
  $tsk.WorkingDirectory = 'C:\bots\ecosys'
  $tsk.IconLocation = 'powershell.exe,0'
  $tsk.Save()
} catch {}

# 9) Final breadcrumb
New-Item -ItemType Directory -Force -Path .\runs | Out-Null
$bundle = 'runs\oh_grand_finish_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
Copy-Item -Force reports\GRAND_READY.txt $bundle  -ErrorAction SilentlyContinue
Copy-Item -Force reports\chat\exact_tail.jsonl $bundle -ErrorAction SilentlyContinue
Write-Ascii 'logs\steps.log' ("`n["+(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')+"] OH-GRAND-FINISH: bundle="+$bundle+"")

Write-Host 'OH GRAND FINISH: done. Background running; Desktop shortcut created: Ecosystem Chat.lnk'