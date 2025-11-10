import os, hashlib, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT/"reports"/"inventory.json"

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20), b""): h.update(chunk)
    return h.hexdigest()

idx=[]
for p in ROOT.parents[0].glob("**/*"):
    try:
        if p.is_file() and p.stat().st_size<5_000_000:
            idx.append({"path":str(p), "bytes":p.stat().st_size, "sha256":sha256(p)})
    except Exception: pass
OUT.write_text(json.dumps({"root":str(ROOT),"files":idx}, indent=2), encoding="utf-8")
print(str(OUT))
