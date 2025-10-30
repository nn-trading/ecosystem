import re, io
p = r"C:\\bots\\ecosys\\tools\\winui_pid.py"
s = io.open(p,'r',encoding='utf-8').read()

def dedup(name: str, text: str):
    # Match def name(...): <block> up to next def or end
    pat = re.compile(r"\n(def\s+"+re.escape(name)+r"\s*\([^\)]*\):(?:(?!\n\s*def\s).|\n(?!\s*def\s))*\n?)", re.S)
    ms = list(pat.finditer(text))
    if len(ms) <= 1:
        return text, 0
    keep = ms[-1]
    out = text
    # Remove earlier blocks from start to ensure uniqueness
    for m in ms[:-1]:
        out = out.replace(m.group(1), "\n", 1)
    return out, len(ms)-1

changed_total = 0
for fn in ('list_windows','count_windows'):
    s, n = dedup(fn, s)
    changed_total += n
io.open(p,'w',encoding='ascii',errors='ignore').write(s)
print({'dedup_removed': changed_total})
