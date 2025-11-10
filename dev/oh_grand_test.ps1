param()
$ErrorActionPreference = "Stop"

function Write-Ascii([string]$Path, [string]$Text){
  $d = Split-Path -Parent $Path; if ($d) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
  [IO.File]::WriteAllText($Path, $Text, [Text.Encoding]::ASCII)
}

# 0) Prep dirs + store API key (no echo)
New-Item -ItemType Directory -Force -Path .\dev, .\config, .\reports\chat, .\runs, .\logs | Out-Null
Set-Content -Encoding Ascii -LiteralPath '.\api_key.txt' -Value 'REDACTED'

# 1) Configs to kill echo + set model
Write-Ascii 'config\comms.yaml' @"
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
"@
Write-Ascii 'config\model.yaml' @"
default: gpt-5
"@

# 2) Brain Chat shell (immediate LLM + planner; ASCII-only; no temperature param)
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
    py = str(ROOT/".venv"/"Scripts"/"python.exe")
    if not pathlib.Path(py).exists(): py = "python"
    try: subprocess.run([py, "dev/eco_cli.py", "ask", q], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    try: subprocess.run([py, "dev/core02_planner.py", "apply"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def try_model(q):
    key_path = ROOT/"api_key.txt"
    key = key_path.read_text().strip() if key_path.exists() else os.environ.get("OPENAI_API_KEY","")
    if not key: return "(no assistant reply yet  put key into api_key.txt)"
    try:
        from openai import OpenAI
    except Exception as e:
        return asc(f"(model error: openai sdk missing: {e})")
    try:
        client = OpenAI(api_key=key)
        sys_prompt = (
            "You are the Ecosystem Brain on Windows. "
            "Answer directly and helpfully without asking for goals. Be concise. "
            "For PC actions, briefly outline steps you will take."
        )
        r = client.chat.completions.create(model=model_name, messages=[
            {"role":"system","content":sys_prompt},
            {"role":"user","content":q}
        ])
        return asc((r.choices[0].message.content or "").strip())
    except Exception as e:
        return asc(f"(model error: {e})")

def main():
    global model_name
    print('Brain chat ready. Type "exit" to quit.')
    print(f'(model={model_name})')
    (ROOT/"dev"/"__init__.py").touch()
    while True:
        try: q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower()=="exit": break
        if q.lower().startswith("/model"):
            parts=q.split(None,1)
            if len(parts)==2 and parts[1].strip():
                model_name = parts[1].strip(); print(f"(model set to {model_name})"); continue
            else:
                print(f"(current model {model_name})"); continue
        append("user", q); try_planner(q)
        ans = try_model(q); append("assistant", ans); print(ans)
    print("Bye.")
if __name__=="__main__": main()
'@
Write-Ascii 'dev\brain_chat_shell.py' $brain
if (-not (Test-Path 'dev\__init__.py')) { Write-Ascii 'dev\__init__.py' '' }

# 3) One-click runner
$runner = @'
param()
$ErrorActionPreference = "Stop"
$py = ".\.venv\Scripts\python.exe"; if (-not (Test-Path $py)) { $py = "python" }
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& $py -m dev.brain_chat_shell
'@
Write-Ascii 'dev\run_chat_full.ps1' $runner

# 4) Stop  vacuum  checkpoint  start background
try { powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null } catch {}
if (Test-Path '.\maintain.ps1') { try { powershell -NoProfile -File .\maintain.ps1 -VacuumDbs 1 | Out-Null } catch {} }
# SQLite checkpoint to clear locks if any
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }
$chk = @'
import sqlite3, pathlib, sys
db = pathlib.Path("var/events.db")
if db.exists():
    try:
        con = sqlite3.connect(db, timeout=5)
        cur = con.cursor()
        cur.execute("PRAGMA wal_checkpoint(FULL)")
        cur.execute("PRAGMA optimize")
        con.commit(); con.close()
        print("OK")
    except Exception as e:
        print("ERR", e)
'@
Write-Ascii 'dev\wal_checkpoint.py' $chk
try { & $py dev\wal_checkpoint.py | Out-Null } catch {}
# Start background (no heavy maintenance)
try { powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null } catch {}

# 5) Route Comms->Brain; disable echo; apply plan; short drain if present
try { & $py dev\chatops_cli.py "Switch Comms to Brain (GPT) mode, disable echo, route bus 'comms/in' to Brain, write replies to reports\\chat\\exact_tail.jsonl" | Out-Null } catch {}
try { & $py dev\core02_planner.py apply | Out-Null } catch {}
try { & $py -m dev.jobs_drain --loops 5 --interval 0.5 | Out-Null } catch {}

# 6) Deep diagnostics: OpenAI call, shell smoke, planner tail, logs proof
$diag = @'
import os, json, time, subprocess, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
REP  = ROOT/"reports"; LOGS = ROOT/"logs"; CHAT = REP/"chat"/"exact_tail.jsonl"
REP.mkdir(parents=True, exist_ok=True); CHAT.parent.mkdir(parents=True, exist_ok=True); CHAT.touch(exist_ok=True)
py = str(ROOT/".venv"/"Scripts"/"python.exe"); 
if not pathlib.Path(py).exists(): py = "python"

def load_model():
    p = ROOT/"config"/"model.yaml"
    try:
        txt = p.read_text(encoding="ascii", errors="ignore")
        m = re.search(r"default:\s*([^\r\n]+)", txt)
        return (m.group(1).strip() if m else "gpt-5")
    except: return "gpt-5"

def test_openai():
    try:
        from openai import OpenAI
    except Exception as e:
        return {"ok": False, "err": f"openai_import:{e}"}
    key = ""
    p = ROOT/"api_key.txt"
    if p.exists(): key = p.read_text().strip()
    if not key: return {"ok": False, "err": "no_api_key"}
    try:
        client = OpenAI(api_key=key)
        model = load_model()
        r = client.chat.completions.create(model=model, messages=[
            {"role":"system","content":"Return only the word READY_OK"},
            {"role":"user","content":"Return only READY_OK"}
        ])
        txt = (r.choices[0].message.content or "").strip()
        return {"ok": "READY_OK" in txt, "resp": txt}
    except Exception as e:
        return {"ok": False, "err": f"openai_call:{e}"}

def shell_smoke():
    cmd = [py, "-m", "dev.brain_chat_shell"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = err = ""
    try:
        p.stdin.write("what is 2+2?\nexit\n"); p.stdin.flush()
        out, err = p.communicate(timeout=25)
    except Exception as e:
        err = f"timeout_or_err:{e}"
    ok = ("4" in out) or (" 4" in out) or ("= 4" in out)
    return {"ok": ok, "out": out[-400:], "err": err[-400:]}

def planner_tail():
    # enqueue one question via planner; then wait for a non-echo assistant line
    try:
        subprocess.run([py, "dev/eco_cli.py", "ask", "diagnostic ping"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([py, "dev/core02_planner.py", "apply"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    end = time.time()+20
    last = None
    while time.time()<end:
        try:
            lines = CHAT.read_text(encoding="ascii", errors="ignore").splitlines()
            for ln in reversed(lines):
                try:
                    o=json.loads(ln)
                    if o.get("role") in ("assistant","brain") and o.get("text") and not str(o.get("text",""))[:5]=="echo:":
                        last = o.get("text"); 
                        if last: return {"ok": True, "text": last[-300:]}
                except: pass
        except: pass
        time.sleep(0.6)
    return {"ok": False, "text": last}

def logs_probe():
    p = LOGS/"start_stdout.log"
    if not p.exists(): return {"ok": False, "err": "no_start_stdout"}
    t = p.read_text(encoding="ascii", errors="ignore")[-2000:]
    ok = ("CORE-02 inbox loop started." in t) and ("JobsWorker started." in t)
    return {"ok": ok, "tail": t}

report = {
  "openai": test_openai(),
  "shell_smoke": shell_smoke(),
  "planner_tail": planner_tail(),
  "logs_probe": logs_probe(),
}
report["overall_ok"] = all(x.get("ok") for x in report.values())
(REP/"GRAND_TEST_REPORT.json").write_text(json.dumps(report, indent=2), encoding="ascii", errors="ignore")
(REP/"GRAND_TEST_SUMMARY.txt").write_text(
    "OPENAI: {0}\nSHELL_SMOKE: {1}\nPLANNER_TAIL: {2}\nLOGS_PROBE: {3}\nOVERALL_OK: {4}\n".format(
        report["openai"], report["shell_smoke"]["ok"], report["planner_tail"]["ok"], report["logs_probe"]["ok"], report["overall_ok"]
    ), encoding="ascii", errors="ignore")
print("OK")
'@
Write-Ascii 'dev\grand_diag.py' $diag
try { & $py dev\grand_diag.py | Out-Null } catch {}

# 7) Desktop shortcut for one-click launch
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

# 8) Bundle + breadcrumb
$bundle = 'runs\oh_grand_test_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
Copy-Item -Force reports\GRAND_TEST_SUMMARY.txt $bundle -ErrorAction SilentlyContinue
Copy-Item -Force reports\GRAND_TEST_REPORT.json $bundle -ErrorAction SilentlyContinue
Copy-Item -Force reports\chat\exact_tail.jsonl $bundle -ErrorAction SilentlyContinue
Write-Ascii 'logs\steps.log' ("`n["+(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')+"] OH-GRAND-TEST: bundle="+$bundle+"")

Write-Host 'OH GRAND TEST: complete. See reports\GRAND_TEST_SUMMARY.txt and Desktop\Ecosystem Chat.lnk'
