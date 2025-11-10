import json
from pathlib import Path
from .local_tools import (
  write_text_file_autoname, write_probe_autoname,
  screenshot_autoname, count_monitors, count_windows
)
res={}
res["monitors"]=count_monitors()
res["windows"]=count_windows()
res["notepad1"]=write_text_file_autoname("E2E NOTEPAD OK","e2e_notepad")
res["notepad2"]=write_text_file_autoname("E2E NOTEPAD OK","e2e_notepad")
res["desk1"]=write_probe_autoname("e2e_probe","OK")
res["desk2"]=write_probe_autoname("e2e_probe","OK")
res["screenshot"]=screenshot_autoname("e2e")
ok=True
try:
  from pathlib import Path as P
  if P(res["notepad1"]).name==P(res["notepad2"]).name: ok=False
  if P(res["desk1"]).name==P(res["desk2"]).name: ok=False
except Exception: ok=False
out={"ok":ok,"artifacts":res}
(R := (Path(__file__).resolve().parents[1]/"reports"/"AUTONAME_OK.json")).write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out))
