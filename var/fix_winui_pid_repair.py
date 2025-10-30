import re, io
p = r"C:\\bots\\ecosys\\tools\\winui_pid.py"
s = io.open(p, 'r', encoding='utf-8').read()
# Find register() start
m_reg = re.search(r"(?m)^def\s+register\s*\(", s)
if not m_reg:
    raise SystemExit("register() not found")
# Find complete paste_pid() block
m_paste = re.search(r"(?ms)^def\s+paste_pid\s*\([^)]*\):.*?(?=^def\s|\Z)", s)
if not m_paste:
    raise SystemExit("paste_pid() block not found")
pre = s[:m_paste.end()].rstrip() + "\n\n"
post = s[m_reg.start():]
# Canonical implementations
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
new_s = pre + fns + post
io.open(p, 'w', encoding='ascii', errors='ignore').write(new_s)
print("winui_pid repaired: inserted single canonical list/count block between paste_pid and register(), stripping stray content")
