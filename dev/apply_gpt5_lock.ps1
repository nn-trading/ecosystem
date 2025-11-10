param()
$ErrorActionPreference='Stop'
$root='C:\bots\ecosys'; if(!(Test-Path $root)){throw 'C:\bots\ecosys not found'}
Set-Location $root
New-Item -ItemType Directory -Force -Path .\configs,.\dev,.\reports\chat | Out-Null

# 1) Config: model hard-locked to GPT-5 (no fallbacks)
@'
default: gpt-5
lock: true
'@ | Set-Content -Encoding Ascii -LiteralPath .\configs\model.yaml

# 2) Brain Chat shell: reads configs/model.yaml, enforces lock==true (no /model switching)
$code = @'
import os, sys, json, time, subprocess, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True)
if not TAIL.exists(): TAIL.write_text("", encoding="ascii", errors="ignore")

def asc(s): return (s or "").encode("ascii","ignore").decode("ascii")
def append(role, text):
    line={"ts":time.strftime("%Y-%m-%d %H:%M:%S"),"role":role,"text":asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f: f.write(json.dumps(line, ensure_ascii=True)+"\n")

def read_model_cfg():
    p = ROOT / "configs" / "model.yaml"
    default, lock = "gpt-5", False
    if p.exists():
        txt = p.read_text(errors="ignore")
        m = re.search(r"(?im)^\s*default\s*:\s*([^\r\n#]+)", txt)
        if m: default = m.group(1).strip().strip('\"\'')
        lk = re.search(r"(?im)^\s*lock\s*:\s*(true|True|1)", txt)
        lock = bool(lk)
    # env can set default only if not locked
    env = os.environ.get("MODEL_NAME","").strip()
    model = default if lock or not env else env
    return model, lock

def run(cmd):
    try: return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
    except Exception: return None

def try_planner(q):
    py = str(ROOT/".venv/Scripts/python.exe")
    if not pathlib.Path(py).exists(): py="python"
    run([py, "dev/eco_cli.py", "ask", q]); run([py, "dev/core02_planner.py", "apply"])

def try_model(q, model_name):
    key_path = ROOT / "api_key.txt"
    key = key_path.read_text().strip() if key_path.exists() else os.environ.get("OPENAI_API_KEY","")
    if not key: return "(no assistant reply yet - put your key in api_key.txt)"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        sys_prompt = "You are the Ecosystem Brain on Windows. Answer directly and helpfully."
        r = client.chat.completions.create(model=model_name, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":q}])
        return asc((r.choices[0].message.content or "").strip())
    except Exception as e:
        return asc(f"(model error: {e})")

def poll_for_reply(timeout=15, min_wait=1.0):
    t0=time.time(); time.sleep(min_wait)
    end=t0+timeout
    while time.time()<end:
        try:
            for ln in reversed(TAIL.read_text(encoding="ascii", errors="ignore").splitlines()):
                try:
                    o=json.loads(ln)
                    if o.get("role") in ("assistant","brain") and o.get("text") and not str(o.get("text",""))[:5]=="echo:":
                        return o["text"]
                except: pass
        except: pass
        time.sleep(0.4)
    return None

def main():
    model_name, locked = read_model_cfg()
    print('Brain chat ready. Type "exit" to quit.')
    print(f"(model={model_name}{' [LOCKED]' if locked else ''})")
    while True:
        try: q=input('You> ').strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower()=='exit': break
        if q.lower().startswith('/model'):
            if locked:
                print('(model is LOCKED to gpt-5)')
            else:
                print(f'(current model {model_name})')
            continue
        if q.lower() in ('/status',):
            print('OK: online; tail:', str(TAIL)); continue
        append('user', q)
        try_planner(q)                 # kick Ecosystem planner track
        ans = try_model(q, model_name) # immediate GPT-5 reply
        append('assistant', ans); print(ans)
        extra = poll_for_reply(timeout=15, min_wait=1.0)
        if extra and not extra.strip()[:5]=="echo:":
            print(f'[ecosystem] {extra}')
    print('Bye.')
if __name__ == '__main__': main()
'@
Set-Content -Encoding Ascii -LiteralPath .\dev\brain_chat_shell.py -Value $code

# 3) Runner: export MODEL_NAME=gpt-5 before launching
$runner = @'
param()
$ErrorActionPreference='Stop'
$ROOT = $PSScriptRoot; if (-not $ROOT) { $ROOT = (Convert-Path '.') }
Set-Location $ROOT
$py = Join-Path $ROOT '.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }
$env:MODEL_NAME = 'gpt-5'
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& $py -m dev.brain_chat_shell
'@
Set-Content -Encoding Ascii -LiteralPath .\dev\run_chat_full.ps1 -Value $runner

# 4) Restart background cleanly and quick self-assert of GPT-5 lock
powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null

$py = '.\.venv\Scripts\python.exe'; if (!(Test-Path $py)) { $py='python' }
$assert = @'
import json, pathlib, re, os
ROOT = pathlib.Path(__file__).resolve().parents[1]
cfg = (ROOT/'configs'/'model.yaml').read_text(errors='ignore')
locked = bool(re.search(r'(?im)^\s*lock\s*:\s*(true|True|1)', cfg))
m = re.search(r'(?im)^\s*default\s*:\s*([^\r\n#]+)', cfg)
model = (m.group(1).strip().strip('"\'')) if m else 'gpt-5'
out = ROOT/'reports'/'GPT5_ASSERT.json'
out.write_text(json.dumps({'default':model,'locked':locked}, indent=2), encoding='utf-8')
print(json.dumps({'default':model,'locked':locked}))
'@
$tmp = Join-Path $root 'dev\_gpt5_assert.py'
Set-Content -Encoding Ascii -LiteralPath $tmp -Value $assert
& $py $tmp | Out-Null
Write-Host 'LOCKED MODEL: ' (Get-Content .\reports\GPT5_ASSERT.json -Raw)
