import sys, subprocess, time
p = subprocess.Popen([sys.executable, "-m", "dev.brain_chat_shell"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
p.stdin.write("hello\nexit\n"); p.stdin.flush()
time.sleep(3)
try: out = p.communicate(timeout=6)[0]
except subprocess.TimeoutExpired:
    p.kill(); out = ""
print(out)