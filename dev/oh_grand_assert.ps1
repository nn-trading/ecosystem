param()
$ErrorActionPreference = "Stop"

function Write-Ascii([string]$Path, [string]$Text){
  $d = Split-Path -Parent $Path; if ($d) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
  [IO.File]::WriteAllText($Path, $Text, [Text.Encoding]::ASCII)
}

# 0) Ensure key, dirs, and baseline files
New-Item -ItemType Directory -Force -Path .\reports\chat, .\runs, .\logs, .\config, .\dev | Out-Null
if (-not (Test-Path '.\api_key.txt')) { throw 'Missing api_key.txt  run the grand test first.' }
if (-not (Test-Path 'config\model.yaml')) { Write-Ascii 'config\model.yaml' "default: gpt-5" }
Write-Ascii 'config\comms.yaml' @"
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
"@

# 1) Stop -> maintain (vacuum) -> WAL checkpoint -> start background
try { powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null } catch {}
if (Test-Path '.\maintain.ps1') { try { powershell -NoProfile -File .\maintain.ps1 -VacuumDbs 1 | Out-Null } catch {} }
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }
$chk = @'
import sqlite3, pathlib
db = pathlib.Path("var/events.db")
if db.exists():
    con = sqlite3.connect(db, timeout=8)
    cur = con.cursor()
    cur.execute("PRAGMA wal_checkpoint(FULL)")
    cur.execute("PRAGMA optimize")
    con.commit(); con.close()
print("OK")
'@
Write-Ascii 'dev\wal_checkpoint.py' $chk
try { & $py dev\wal_checkpoint.py | Out-Null } catch {}
try { powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null } catch {}

# 2) Route Comms->Brain (no echo), apply plan, brief drain
try { & $py dev\chatops_cli.py "Switch Comms to Brain (GPT) mode, disable echo, route bus 'comms/in' to Brain, write replies to reports\\chat\\exact_tail.jsonl" | Out-Null } catch {}
try { & $py dev\core02_planner.py apply | Out-Null } catch {}
try { & $py -m dev.jobs_drain --loops 5 --interval 0.5 | Out-Null } catch {}

# 3) Non-interactive smoke of the chat shell (ensures immediate model path works)
$smoke = @'
import subprocess, pathlib, os, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
py = str(ROOT/".venv"/"Scripts"/"python.exe"); 
if not pathlib.Path(py).exists(): py = "python"
cmd = [py,"-m","dev.brain_chat_shell"]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
out, err = p.communicate("what is 2+2?\nexit\n", timeout=70)
ok = "4" in out
print(json.dumps({"ok":ok, "out":out[-400:], "err":err[-400:]}))
'@
Write-Ascii 'dev\chat_smoke.py' $smoke
$smokeJson = & $py dev\chat_smoke.py
try { $smokeObj = $smokeJson | ConvertFrom-Json } catch { $smokeObj = @{ ok = $false; out = $smokeJson; err = 'json_parse_error' } }

# 4) Deep diagnostics (re-use grand diag)
$diagPath = 'dev\grand_diag.py'
if (-not (Test-Path $diagPath)) {
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
    key = (ROOT/"api_key.txt").read_text().strip() if (ROOT/"api_key.txt").exists() else os.environ.get("OPENAI_API_KEY","")
    if not key: return {"ok": False, "err": "no_api_key"}
    try:
        client = OpenAI(api_key=key); model = load_model()
        r = client.chat.completions.create(model=model, messages=[
            {"role":"system","content":"Return only READY_OK"},
            {"role":"user","content":"Return only READY_OK"}
        ])
        txt = (r.choices[0].message.content or "").strip()
        return {"ok": "READY_OK" in txt, "resp": txt}
    except Exception as e:
        return {"ok": False, "err": f"openai_call:{e}"}

def planner_tail():
    try:
        subprocess.run([py, "dev/eco_cli.py", "ask", "diagnostic ping"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([py, "dev/core02_planner.py", "apply"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    end = time.time()+20
    while time.time()<end:
        try:
            lines = CHAT.read_text(encoding="ascii", errors="ignore").splitlines()
            for ln in reversed(lines):
                try:
                    o=json.loads(ln)
                    if o.get("role") in ("assistant","brain") and o.get("text") and not str(o.get("text","")).startswith("echo:"):
                        return {"ok": True, "text": str(o.get("text"))[-300:]}
                except: pass
        except: pass
        time.sleep(0.6)
    return {"ok": False}

def logs_probe():
    p = LOGS/"start_stdout.log"
    if not p.exists(): return {"ok": False, "err": "no_start_stdout"}
    t = p.read_text(encoding="ascii", errors="ignore")[-2000:]
    ok = ("CORE-02 inbox loop started." in t) and ("JobsWorker started." in t)
    return {"ok": ok}

report = {
  "openai": test_openai(),
  "shell_smoke": {"ok": False, "out": "skipped", "err": "skipped"},
  "planner_tail": planner_tail(),
  "logs_probe": logs_probe(),
}
report["overall_ok"] = all(x.get("ok") for x in report.values())
(REP/"GRAND_TEST_REPORT.json").write_text(json.dumps(report, indent=2), encoding="ascii", errors="ignore")
(REP/"GRAND_TEST_SUMMARY.txt").write_text(
  "OPENAI: {0}\nSHELL_SMOKE: {1}\nPLANNER_TAIL: {2}\nLOGS_PROBE: {3}\nOVERALL_OK: {4}\n".format(
    report["openai"], report["shell_smoke"]["ok"], report["planner_tail"]["ok"], report["logs_probe"]["ok"], report["overall_ok"]),
  encoding="ascii", errors="ignore")
print("OK")
'@
  Write-Ascii $diagPath $diag
}
# Re-run diag but inject our smoke result
try { & $py dev\grand_diag.py | Out-Null } catch {}
# Merge the live smoke outcome into GRAND_TEST_REPORT
$repPath = 'reports\GRAND_TEST_REPORT.json'
if (Test-Path $repPath) {
  try {
    $rep = Get-Content $repPath -Raw -Encoding Ascii | ConvertFrom-Json
    $rep.shell_smoke = @{ ok = [bool]$smokeObj.ok; out = $smokeObj.out; err = $smokeObj.err }
    $rep.overall_ok = [bool]($rep.openai.ok -and $rep.shell_smoke.ok -and $rep.planner_tail.ok -and $rep.logs_probe.ok)
    $json = $rep | ConvertTo-Json -Depth 6
    Set-Content -Encoding Ascii -LiteralPath $repPath -Value $json
  } catch {}
}

# 5) Desktop shortcut (idempotent)
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

# 6) Final assert summary
$summary = ""
try {
  $rep = Get-Content 'reports\GRAND_TEST_REPORT.json' -Raw -Encoding Ascii | ConvertFrom-Json
  $ok = [bool]$rep.overall_ok
  $summary = "OPENAI_OK=$($rep.openai.ok)  SHELL_OK=$($rep.shell_smoke.ok)  PLANNER_OK=$($rep.planner_tail.ok)  LOGS_OK=$($rep.logs_probe.ok)  OVERALL_OK=$ok"
  Write-Ascii 'reports\GRAND_ASSERT.txt' $summary
  if ($ok) { Write-Ascii 'reports\GRAND_OK.flag' 'OK' }
} catch {
  $summary = 'FAILED_TO_PARSE_DIAG'
  Write-Ascii 'reports\GRAND_ASSERT.txt' $summary
}

# 7) Bundle + breadcrumb
$bundle = 'runs\oh_grand_assert_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
foreach ($f in @('reports\GRAND_ASSERT.txt','reports\GRAND_TEST_SUMMARY.txt','reports\GRAND_TEST_REPORT.json','reports\chat\exact_tail.jsonl','logs\start_stdout.log','logs\start_stderr.log')) { if (Test-Path $f) { Copy-Item -Force $f $bundle -ErrorAction SilentlyContinue } }
Write-Ascii 'logs\steps.log' ("`n["+(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')+"] OH-GRAND-ASSERT: bundle="+$bundle+"")

Write-Host ('OH GRAND ASSERT complete: ' + $summary)
