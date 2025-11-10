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