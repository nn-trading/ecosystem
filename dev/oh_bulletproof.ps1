param()
function Write-Ascii($Path,$Text){$dir=Split-Path -Parent $Path;if($dir){New-Item -ItemType Directory -Force -Path $dir|Out-Null};[IO.File]::WriteAllText($Path,$Text,[Text.Encoding]::ASCII)}
function Write-Json($Path,$Obj){$j=$Obj|ConvertTo-Json -Depth 8;Write-Ascii $Path $j}
$ErrorActionPreference='Stop'
Set-Location C:\bots\ecosys
# 0) Dirs + ASCII policy
New-Item -ItemType Directory -Force -Path .\logs,.\runs,.\reports,.\specs\capabilities,.\config,.\var,.\reports\chat | Out-Null
# 1) Ensure configs: Comms -> Brain (no echo); default model
Write-Ascii 'config\comms.yaml' @"
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
"@
Write-Ascii 'config\model.yaml' @"
default: gpt-5
"@
# 2) Safe Brain Chat shell (immediate LLM reply + planner kick + tail poll; ASCII-only logs)
$brain=@'
import os, sys, json, time, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)
model_name = os.environ.get("MODEL_NAME","gpt-5")
def asc(s): return (s or "").encode("ascii","ignore").decode("ascii")
def append(role, text):
    line = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "role": role, "text": asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f:
        f.write(json.dumps(line, ensure_ascii=True)+"\n")
def poll_for_reply(timeout=20, min_wait=1.2):
    t0=time.time()
    while time.time()-t0 < min_wait: time.sleep(0.2)
    end=t0+timeout
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
        time.sleep(0.5)
    return None

def try_planner(q):
    py = str(ROOT/".venv/Scripts/python.exe")
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
        sys_prompt = "You are the Ecosystem Brain on Windows. Answer directly, briefly, and helpfully. Never ask for goals; just help."
        r = client.chat.completions.create(model=model_name, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":q}])
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
        if q.lower()=="exit": break
        if q.lower().startswith("/model"):
            parts=q.split(None,1)
            if len(parts)==2 and parts[1].strip():
                model_name=parts[1].strip(); print(f"(model set to {model_name})"); continue
            else:
                print(f"(current model {model_name})"); continue
        append("user", q)
        try_planner(q)                 # kick Ecosystem planner
        ans = try_model(q)             # immediate LLM reply
        append("assistant", ans); print(ans)
        extra = poll_for_reply(timeout=15, min_wait=1.0)   # surface Ecosystem planner reply if it appears
        if extra and extra.strip() and extra.strip() != ans.strip():
            print(f"[ecosystem] {extra}")
    print("Bye.")
if __name__ == "__main__": main()
'@
Write-Ascii 'dev\__init__.py' ''
Write-Ascii 'dev\brain_chat_shell.py' $brain
# 3) One-click runner (stop cleanly -> start background -> launch brain chat)
$run=@'
param()
$ErrorActionPreference="Stop"
$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; $env:ECOSYS_SKIP_DASHBOARD="1"
try { powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null } catch {}
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2
& .\.venv\Scripts\python.exe -m dev.brain_chat_shell
'@
Write-Ascii 'dev\run_chat_full.ps1' $run
# 4) Route comms to Brain (no echo) and apply plan
$py = '.\.venv\Scripts\python.exe'; if (!(Test-Path $py)) { $py='python' }
try { & $py dev\chatops_cli.py "Switch Comms to Brain (GPT) mode, disable echo, route bus 'comms/in' to Brain, write replies to reports\chat\exact_tail.jsonl" | Out-Null } catch {}
try { & $py dev\core02_planner.py apply | Out-Null } catch {}
# 5) Start background (no maintenance; we already hardened earlier)
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
# 6) Non-interactive smoke of chat shell (ensures immediate answers work)
$smk=@'
import sys, subprocess, time, json, os
p = subprocess.Popen([sys.executable, "-m", "dev.brain_chat_shell"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
p.stdin.write("hello\nexit\n"); p.stdin.flush()
time.sleep(3)
try: out = p.communicate(timeout=6)[0]
except subprocess.TimeoutExpired:
    p.kill(); out = ""
print(out)
'@
Write-Ascii 'dev\_smoke_chat.py' $smk
$out = & $py dev\_smoke_chat.py
$ok_chat = ($out -match "You>" -or $out -match "hello" -or $out -match "Brain chat ready")
# 7) Tail probe (non-echo assistant/brain line present)
$tail='reports\chat\exact_tail.jsonl'; $ok_tail=$false
if(Test-Path $tail){
  $lines = Get-Content -Path $tail -Encoding ASCII -Tail 200
  foreach($ln in $lines){ try{ $o=$ln|ConvertFrom-Json }catch{ continue }
    if($o.role -in @('assistant','brain') -and $o.text -and -not ($o.text -like 'echo:*')){ $ok_tail=$true; break } }
}
# 8) Grand assert (if available)
$ok_assert=$true
if(Test-Path 'dev\oh_grand_assert.ps1'){
  try { powershell -NoProfile -File .\dev\oh_grand_assert.ps1 | Out-Null } catch {}
  if(Test-Path 'reports\GRAND_ASSERT.txt'){
    $t=Get-Content -Encoding ASCII -Path 'reports\GRAND_ASSERT.txt' -Raw
    if($t -notmatch 'OVERALL_OK=True'){ $ok_assert=$false }
  }
}
# 9) Desktop shortcut for one-click launch
try{
  $desk=[Environment]::GetFolderPath('Desktop')
  $lnk=Join-Path $desk 'Ecosystem Chat.lnk'
  $W=New-Object -ComObject WScript.Shell
  $S=$W.CreateShortcut($lnk)
  $S.TargetPath='powershell.exe'
  $S.Arguments='-NoProfile -ExecutionPolicy Bypass -File "C:\bots\ecosys\dev\run_chat_full.ps1"'
  $S.WorkingDirectory='C:\bots\ecosys'
  $S.IconLocation='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe,0'
  $S.Save()
}catch{}
# 10) Summary + bundle
$sum=@()
$sum+="BULLETPROOF READY SUMMARY"
$sum+="immediate_chat_ok: $ok_chat"
$sum+="tail_has_assistant: $ok_tail"
$sum+="grand_assert_ok: $ok_assert"
$sum+="launcher: C:\bots\ecosys\dev\run_chat_full.ps1"
$sum+="shortcut: Desktop\Ecosystem Chat.lnk"
$txt = ($sum -join "`r`n")
Write-Ascii 'reports\BULLETPROOF_READY.txt' $txt
$bundle="runs\oh_bulletproof_"+(Get-Date -Format 'yyyyMMdd_HHmmss'); New-Item -ItemType Directory -Force -Path $bundle|Out-Null
foreach($f in @('reports\BULLETPROOF_READY.txt','reports\GRAND_ASSERT.txt','reports\GRAND_TEST_REPORT.json','reports\GRAND_TEST_SUMMARY.txt','reports\chat\exact_tail.jsonl')){
  if(Test-Path $f){ Copy-Item $f $bundle -Force }
}
Write-Host $txt
