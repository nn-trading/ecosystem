import json, sys
sys.path.insert(0, r"C:\bots\ecosys")
import tools.winui_pid as m
res = m.count_windows()
print(json.dumps({"ok": res.get("ok"), "count": res.get("count")}))
