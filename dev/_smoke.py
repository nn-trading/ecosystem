import json, pathlib, dev.local_tools as t
out = {
  "monitors": t.count_monitors(),
  "windows":  t.count_windows(),
  "titles":   t.list_titles(15),
  "shot":     t.screenshot("ready")
}
path = pathlib.Path("reports")/"READY_STATUS.json"
path.write_text(json.dumps(out, ensure_ascii=True, indent=2))
print(json.dumps(out, ensure_ascii=True))
