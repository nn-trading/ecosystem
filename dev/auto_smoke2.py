import json, time
from pathlib import Path
from .local_tools import (
    notepad_save_text_autoname, desktop_write_autoname,
    screenshot_autoname, count_monitors, count_windows
)

res={}
res["monitors"]=count_monitors()
res["windows"]=count_windows()
res["notepad1"]=notepad_save_text_autoname("E2E NOTEPAD OK","e2e_notepad")
time.sleep(0.8)
res["notepad2"]=notepad_save_text_autoname("E2E NOTEPAD OK","e2e_notepad")
res["desk1"]=desktop_write_autoname("OK","e2e_probe")
res["desk2"]=desktop_write_autoname("OK","e2e_probe")
res["screenshot"]=screenshot_autoname("e2e")

ok=True
try:
    if not res["notepad1"] or not res["notepad2"]: ok=False
    else:
        p1=Path(res["notepad1"]); p2=Path(res["notepad2"])
        if p1.exists() and p2.exists() and p1.name==p2.name: ok=False
    if res["desk1"] and res["desk2"] and Path(res["desk1"]).name==Path(res["desk2"]).name: ok=False
except Exception:
    ok=False

out={"ok": ok, "artifacts": res}
RPTS=Path(__file__).resolve().parents[1]/"reports"
RPTS.mkdir(parents=True, exist_ok=True)
(RPTS/"AUTONAME_OK.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out))
