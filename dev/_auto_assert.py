import time, os, sys, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from dev import local_tools as LT

desk = pathlib.Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
ok_path = desk/"eco_ok.txt"
LT.open_app("notepad.exe"); time.sleep(0.8)
LT.type_text("Ecosystem OK"); time.sleep(0.2)
LT.keys("ctrl+s"); time.sleep(0.5)
LT.type_text(str(ok_path)); time.sleep(0.2)
LT.keys("enter"); time.sleep(0.6)
shot = LT.screenshot()
out = {"ok_file": str(ok_path), "screenshot": shot, "monitors": LT.count_monitors(), "windows": LT.count_windows()}
(pathlib.Path("reports")/"AUTO_ASSERT.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({"ok":True}))
