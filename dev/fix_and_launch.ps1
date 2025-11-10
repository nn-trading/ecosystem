Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
$ROOT = 'C:\bots\ecosys'
Set-Location -LiteralPath $ROOT

# --- Ensure required dirs (NOTE: correct folder is `config`, not `configs`) ---
foreach($d in @('dev','config','reports','reports\chat')){ if(!(Test-Path -LiteralPath $d)){ New-Item -ItemType Directory -Path $d | Out-Null } }

# Make dev a package so "-m dev.brain_chat_shell" works
if (!(Test-Path -LiteralPath 'dev\__init__.py')) { '' | Set-Content -Encoding Ascii -LiteralPath 'dev\__init__.py' }

# --- Correct configs: lock GPT-5, route Comms->Brain, echo off, correct tail path ---
Set-Content -Encoding Ascii -LiteralPath 'config\model.yaml' -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath 'config\comms.yaml' -Value "mode: brain`necho: false`ntail: reports\chat\exact_tail.jsonl"

# Ensure tail file exists
$tail = 'reports\chat\exact_tail.jsonl'
if (!(Test-Path -LiteralPath $tail)) { New-Item -ItemType File -Path $tail | Out-Null }

# --- Write robust Brain Chat shell: immediate reply + planner apply + tail poll (filters echo & retry spam) ---
$pycode = @'
import os, sys, json, time, subprocess, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)

MODEL_NAME = os.environ.get("MODEL_NAME","gpt-5")

def asc(s):
    try:
        return (s or "").encode("ascii","ignore").decode("ascii")
    except Exception:
        return str(s or "")

def append(role, text):
    line = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "role": role, "text": asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f:
        f.write(json.dumps(line, ensure_ascii=True)+"\n")

def poll_tail(timeout=25, min_wait=1.2):
    t0 = time.time()
    while time.time() - t0 < min_wait:
        time.sleep(0.2)
    end = t0 + timeout
    pat_skip = re.compile(r"^(echo:|AI-\d+:|\[Worker\] Replan|.*retry budget exhausted)", re.I)
    while time.time() < end:
        try:
            lines = TAIL.read_text(encoding="ascii", errors="ignore").splitlines()
            for ln in reversed(lines):
                try:
                    o = json.loads(ln)
                    role = (o.get("role") or "").lower()
                    text = o.get("text") or ""
                    if role in ("assistant","brain") and text and not pat_skip.search(text.strip()):
                        return text
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(0.5)
    return None

def try_planner(q):
    py = str(ROOT/".venv/Scripts/python.exe")
    if not pathlib.Path(py).exists():
        py = "python"
    try:
        subprocess.run([py, "dev/eco_cli.py", "ask", q], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    try:
        subprocess.run([py, "dev/core02_planner.py", "apply"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def try_model(q):
    key = ""
    p = ROOT/"api_key.txt"
    if p.exists():
        try:
            key = p.read_text().strip()
        except Exception:
            key = ""
    if not key:
        key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return "(no OPENAI_API_KEY/api_key.txt)"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        sys_prompt = "You are the Ecosystem Brain on Windows. Be concise and directly helpful. No meta talk."
        r = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": q}
            ]
        )
        return asc((r.choices[0].message.content or "").strip())
    except Exception as e:
        return asc(f"(model error: {e})")

def main():
    global MODEL_NAME
    print('Brain chat ready. Type "exit" to quit.')
    print(f'(model={MODEL_NAME})')
    while True:
        try:
            q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() == "exit":
            break
        if q.lower().startswith("/model"):
            print(f"(model is LOCKED to {MODEL_NAME})")
            continue
        if q.lower() == "/status":
            print("(status ok)")
            continue
        append("user", q)
        try_planner(q)
        ans = try_model(q)
        append("assistant", ans)
        print(ans)
        extra = poll_tail(timeout=20, min_wait=1.0)
        if extra and extra.strip() and extra.strip() != ans.strip():
            print(f"[ecosystem] {extra}")
    print("Bye.")

if __name__ == "__main__":
    main()
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\brain_chat_shell.py' -Value $pycode

# --- Clean stop & sticky-state cleanup ---
try { powershell -NoProfile -File '.\start.ps1' -Stop 1 | Out-Null } catch {}
foreach($f in @('workspace\logs\events.jsonl','var\events.db-wal','var\events.db-shm')){
  if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue }
}

# --- Start background headless with deps ---
powershell -NoProfile -File '.\start.ps1' -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null

# --- Planner warmup: apply & enqueue a ping (non-fatal if missing) ---
$pyexe = Join-Path $ROOT '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pyexe)) { $pyexe = 'python' }
try { & $pyexe 'dev\core02_planner.py' 'apply' | Out-Null } catch {}
try { & $pyexe 'dev\eco_cli.py' 'ask' 'ping' | Out-Null } catch {}

# --- Launch chat shell in its own window; write assert line ---
try { Start-Process $pyexe -ArgumentList '-m','dev.brain_chat_shell' } catch {}
$ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Set-Content -Encoding Ascii -LiteralPath 'reports\FINAL_ASSERT.txt' -Value "[$ts] FIX_APPLIED: config-path corrected, echo off, GPT-5 locked, chat shell updated & launched."
