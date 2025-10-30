import re, io
p = r"C:\\bots\\ecosys\\tools\\winui_pid.py"
s = io.open(p, 'r', encoding='utf-8').read()
# Remove all list_windows/count_windows definitions
s1 = re.sub(r"(?ms)^\s*def\s+list_windows\s*\([^)]*\):.*?(?=^\s*def\s|\Z)", "", s)
s2 = re.sub(r"(?ms)^\s*def\s+count_windows\s*\([^)]*\):.*?(?=^\s*def\s|\Z)", "", s1)
# Insert canonical implementations just before register()
m = re.search(r"(?m)^def\s+register\s*\(", s2)
if not m:
    raise SystemExit("register() not found in winui_pid.py")
fns = """

def list_windows(visible_only: bool = True, titled_only: bool = True) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for h in _enum_windows():
        pid = _get_pid(h)
        title = _get_title(h)
        vis = _is_visible(h)
        if visible_only and not vis:
            continue
        if titled_only and not title:
            continue
        items.append({"hwnd": int(h), "pid": int(pid), "title": title, "visible": bool(vis)})
    return {"ok": True, "count": len(items), "windows": items}


def count_windows(visible_only: bool = True, titled_only: bool = True) -> Dict[str, Any]:
    res = list_windows(visible_only=visible_only, titled_only=titled_only)
    if not isinstance(res, dict) or not res.get("ok"):
        return {"ok": False, "error": "failed to list windows"}
    return {"ok": True, "count": int(res.get("count", 0))}
"""
new_s = s2[:m.start()] + fns + "\n" + s2[m.start():]
io.open(p, 'w', encoding='ascii', errors='ignore').write(new_s)
print("winui_pid: deduplicated list_windows/count_windows and restored canonical versions")
