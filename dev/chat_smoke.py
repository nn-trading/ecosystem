import subprocess, pathlib, os, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
py = str(ROOT/".venv"/"Scripts"/"python.exe"); 
if not pathlib.Path(py).exists(): py = "python"
cmd = [py,"-m","dev.brain_chat_shell"]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
out, err = p.communicate("what is 2+2?\nexit\n", timeout=70)
ok = "4" in out
print(json.dumps({"ok":ok, "out":out[-400:], "err":err[-400:]}))