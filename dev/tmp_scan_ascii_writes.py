import os, re, sys
root = r"C:\\bots\\ecosys"
pat_w = re.compile(r"(?:io\.)?open\([^\)]*['\"](?:w|a)['\"][^\)]*encoding\s*=\s*['\"]utf-?8['\"][^\)]*\)")
pat_wt = re.compile(r"write_text\([^\)]*encoding\s*=\s*['\"]utf-?8['\"][^\)]*\)")
pat_json = re.compile(r"ensure_ascii\s*=\s*False")

hits = []
for dp, dn, fn in os.walk(root):
    if '.venv' in dp.split(os.sep):
        continue
    for f in fn:
        if f.endswith('.py'):
            p = os.path.join(dp, f)
            try:
                s = open(p, 'r', encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            if pat_w.search(s) or pat_wt.search(s) or pat_json.search(s):
                for ln, line in enumerate(s.splitlines(), 1):
                    if (pat_w.search(line) or pat_wt.search(line) or pat_json.search(line)):
                        hits.append(f"{p}|{ln}|{line.strip()}")

sys.stdout.write("\n".join(hits))
