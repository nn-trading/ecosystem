import re, io
p = r"C:\\bots\\ecosys\\tools\\winui_pid.py"
s = io.open(p,'r',encoding='utf-8').read()

def find_blocks(name: str, text: str):
    starts = [m.start() for m in re.finditer(r"(?m)^def\\s+"+name+r"\\s*\\(", text)]
    blocks = []
    for i, st in enumerate(starts):
        mnext = re.search(r"(?m)^def\\s+", text[st+1:])
        if mnext:
            en = st + 1 + mnext.start()
        else:
            en = len(text)
        blocks.append((st, en))
    return blocks

remove_spans = []
for nm in ("list_windows","count_windows"):
    blks = find_blocks(nm, s)
    if len(blks) > 1:
        remove_spans.extend(blks[1:])  # keep first, remove others

if remove_spans:
    remove_spans.sort(key=lambda t: t[0], reverse=True)
    for st, en in remove_spans:
        s = s[:st] + "\n" + s[en:]
    io.open(p,'w',encoding='ascii',errors='ignore').write(s)
print({"removed_blocks": len(remove_spans)})
