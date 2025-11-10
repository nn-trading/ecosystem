import os, json, pathlib, time
out = {"ts": time.strftime("%Y-%m-%d %H:%M:%S")}
ROOT = pathlib.Path(__file__).resolve().parents[1]

def asc(s):
    try: return (s or "").encode("ascii","ignore").decode("ascii")
    except: return str(s or "")

# tools
try:
    import dev.local_tools as t
    out["TOOLS_IMPORT_OK"]=True
    out["monitors"]=t.count_monitors()
    out["windows"]=t.count_windows()
    out["titles"]=t.list_titles(10)
    out["screenshot"]=t.screenshot("fixpack")
except Exception as e:
    out["TOOLS_IMPORT_OK"]=False
    out["TOOLS_ERROR"]=asc(e)

# openai connectivity (optional)
try:
    from openai import OpenAI
    key=""
    kp=ROOT/'api_key.txt'
    if kp.exists(): key=kp.read_text().strip()
    if not key: key=os.environ.get("OPENAI_API_KEY","")
    if key:
        client=OpenAI(api_key=key)
        r=client.chat.completions.create(model=os.environ.get("MODEL_NAME","gpt-5"), messages=[{"role":"user","content":"ping"}])
        out["OPENAI_OK"]=True
    else:
        out["OPENAI_OK"]=False
        out["OPENAI_ERROR"]="no key"
except Exception as e:
    out["OPENAI_OK"]=False
    out["OPENAI_ERROR"]=asc(e)

p1 = ROOT/'reports'/'FIXPACK_ASSERT.json'
p1.write_text(json.dumps(out, ensure_ascii=True, indent=2))
p2 = ROOT/'reports'/'FIXPACK_SUMMARY.txt'
lines=[
  "FIX PACK SUMMARY",
  "ts: "+out.get("ts",""),
  "TOOLS_IMPORT_OK: "+str(out.get("TOOLS_IMPORT_OK")),
  "OPENAI_OK: "+str(out.get("OPENAI_OK")),
  "monitors: "+str(out.get("monitors")),
  "windows: "+str(out.get("windows")),
  "screenshot: "+str(out.get("screenshot"))
]
p2.write_text("\n".join(lines), encoding="ascii", errors="ignore")
print(json.dumps(out, ensure_ascii=True))
