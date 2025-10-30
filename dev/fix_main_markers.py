import os, sys, re

p = r"C:\bots\ecosys\main.py"
s = open(p,"r",encoding="utf-8").read()
orig = s

# Enforce exact forms (double underscores)
s = s.replace("from future import annotations", "from future import annotations")
s = s.replace("os.path.abspath(file)", "os.path.abspath(file)")
s = s.replace('if name == "main":', 'if name == "main":')

open(p,"w",encoding="ascii",errors="ignore").write(s)

# Verify
t = open(p,"r",encoding="utf-8").read()
print("VERIFY:")
print(" - future import:", "PASS" if "from future import annotations" in t else "FAIL")
print(" - file cwd:",      "PASS" if "os.path.abspath(file)" in t else "FAIL")
print(' - name guard:',    'PASS' if 'if name == "main":' in t else "FAIL")
