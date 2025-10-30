import io, re
p = r"C:\\bots\\ecosys\\tools\\winui_pid.py"
s = io.open(p, 'r', encoding='utf-8').read()
# Locate key anchors
pos_paste = s.find('def paste_pid(')
if pos_paste == -1:
    raise SystemExit('paste_pid not found')
pos_register = s.find('def register(')
if pos_register == -1:
    raise SystemExit('register not found')
# Find the end of paste_pid by locating its specific return line (last line of fn)
ret_marker = 'return {"ok": True, "pid": int(pid), "hwnd": hwnd, "text": txt}'
pos_ret = s.find(ret_marker, pos_paste)
if pos_ret == -1:
    raise SystemExit('paste_pid return marker not found')
# Advance to end of that line
endline = s.find('\n', pos_ret)
if endline == -1:
    endline = len(s)
end_of_paste = endline + 1
prefix = s[:end_of_paste].rstrip() + "\n\n"
suffix = s[pos_register:]
# Canonical list/count implementations
canon = (
    "def list_windows(visible_only: bool = True, titled_only: bool = True) -> Dict[str, Any]:\n"
    "    items: List[Dict[str, Any]] = []\n"
    "    for h in _enum_windows():\n"
    "        pid = _get_pid(h)\n"
    "        title = _get_title(h)\n"
    "        vis = _is_visible(h)\n"
    "        if visible_only and not vis:\n"
    "            continue\n"
    "        if titled_only and not title:\n"
    "            continue\n"
    "        items.append({\"hwnd\": int(h), \"pid\": int(pid), \"title\": title, \"visible\": bool(vis)})\n"
    "    return {\"ok\": True, \"count\": len(items), \"windows\": items}\n\n\n"
    "def count_windows(visible_only: bool = True, titled_only: bool = True) -> Dict[str, Any]:\n"
    "    res = list_windows(visible_only=visible_only, titled_only=titled_only)\n"
    "    if not isinstance(res, dict) or not res.get(\"ok\"):\n"
    "        return {\"ok\": False, \"error\": \"failed to list windows\"}\n"
    "    return {\"ok\": True, \"count\": int(res.get(\"count\", 0))}\n\n"
)
new_s = prefix + canon + suffix
io.open(p, 'w', encoding='ascii', errors='ignore').write(new_s)
print('Cleaned winui_pid: kept paste_pid, inserted canonical list/count, removed stray blocks before register()')
