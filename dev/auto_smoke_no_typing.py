import json
from pathlib import Path
from .local_tools import (
    write_text_file_autoname, open_notepad,
    screenshot_autoname, count_monitors, count_windows
)

res={}
res["monitors"]=count_monitors()
res["windows"]=count_windows()

# create two different files without any UI typing
res["notepad1"]=write_text_file_autoname("E2E NOTEPAD OK", "e2e_notepad")
res["notepad2"]=write_text_file_autoname("E2E NOTEPAD OK", "e2e_notepad")

# optional: just show the first file (no typing)
try:
    open_notepad(res["notepad1"])
except Exception:
    pass

# two desktop probes with unique names too
from .auto_utils import unique_path
desk = Path.home() / "Desktop"
p3 = Path(unique_path(desk, "e2e_probe", ".txt"))
p3.write_text("OK", encoding="utf-8"); res["desk1"]=str(p3)
p4 = Path(unique_path(desk, "e2e_probe", ".txt"))
p4.write_text("OK", encoding="utf-8"); res["desk2"]=str(p4)

res["screenshot"]=screenshot_autoname("e2e")

ok=True
try:
    if Path(res["notepad1"]).name == Path(res["notepad2"]).name: ok=False
    if Path(res["desk1"]).name == Path(res["desk2"]).name: ok=False
except Exception:
    ok=False

out={"ok": ok, "artifacts": res}
RPTS = Path(__file__).resolve().parents[1]/"reports"
RPTS.mkdir(parents=True, exist_ok=True)
(RPTS/"AUTONAME_OK.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out))
