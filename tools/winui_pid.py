# C:\bots\ecosys\tools\winui_pid.py
from __future__ import annotations
import os, time, ctypes
from ctypes import wintypes
from typing import Any, Dict, Optional, List

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

HWND   = wintypes.HWND
DWORD  = wintypes.DWORD
LPARAM = wintypes.LPARAM
WPARAM = wintypes.WPARAM
try:
    LRESULT = wintypes.LRESULT
except AttributeError:
    try:
        LRESULT = wintypes.LPARAM
    except Exception:
        LRESULT = ctypes.c_size_t
BOOL   = wintypes.BOOL
UINT   = wintypes.UINT
LPWSTR = wintypes.LPWSTR

SW_RESTORE         = 9
WM_GETTEXTLENGTH   = 0x000E
WM_GETTEXT         = 0x000D
WM_SETTEXT         = 0x000C
WM_COPY            = 0x0301
WM_PASTE           = 0x0302

DANGER = os.environ.get("AGENT_DANGER_MODE", "1") == "1"

EnumWindowsProc = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
user32.EnumWindows.argtypes = [EnumWindowsProc, LPARAM]
user32.EnumWindows.restype  = BOOL

user32.IsWindowVisible.argtypes = [HWND]
user32.IsWindowVisible.restype  = BOOL

user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]
user32.GetWindowThreadProcessId.restype  = DWORD

user32.GetWindowTextLengthW.argtypes = [HWND]
user32.GetWindowTextLengthW.restype  = ctypes.c_int

user32.GetWindowTextW.argtypes = [HWND, LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype  = ctypes.c_int

user32.SetForegroundWindow.argtypes = [HWND]
user32.SetForegroundWindow.restype  = BOOL

user32.BringWindowToTop.argtypes = [HWND]
user32.BringWindowToTop.restype  = BOOL

user32.ShowWindow.argtypes = [HWND, ctypes.c_int]
user32.ShowWindow.restype  = BOOL

user32.AttachThreadInput.argtypes = [DWORD, DWORD, BOOL]
user32.AttachThreadInput.restype  = BOOL

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype  = HWND

user32.FindWindowExW.argtypes = [HWND, HWND, LPWSTR, LPWSTR]
user32.FindWindowExW.restype  = HWND

user32.SetFocus.argtypes = [HWND]
user32.SetFocus.restype  = HWND

user32.SendMessageW.argtypes = [HWND, UINT, WPARAM, LPARAM]
user32.SendMessageW.restype  = LRESULT

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype  = DWORD

def _enum_windows() -> list[int]:
    handles: list[int] = []
    @EnumWindowsProc
    def _cb(hwnd, lparam):
        handles.append(int(hwnd))
        return True
    user32.EnumWindows(_cb, 0)
    return handles

def _get_pid(hwnd: int) -> int:
    pid = DWORD(0)
    user32.GetWindowThreadProcessId(HWND(hwnd), ctypes.byref(pid))
    return int(pid.value)

def _is_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(HWND(hwnd)))

def _get_title(hwnd: int) -> str:
    n = user32.GetWindowTextLengthW(HWND(hwnd))
    if n <= 0: return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(HWND(hwnd), buf, n + 1)
    return buf.value

def _find_top_hwnd_for_pid(pid: int) -> Optional[int]:
    best = None
    for h in _enum_windows():
        if _get_pid(h) == pid and _is_visible(h):
            if _get_title(h):  # prefer titled window
                return h
            if best is None:
                best = h
    return best

def _find_first_edit(hwnd_parent: int) -> Optional[int]:
    child = user32.FindWindowExW(HWND(hwnd_parent), HWND(0), "Edit", None)
    if child:
        return int(child)
    after = HWND(0)
    while True:
        child = user32.FindWindowExW(HWND(hwnd_parent), after, None, None)
        if not child:
            break
        after = child
        sub = user32.FindWindowExW(child, HWND(0), "Edit", None)
        if sub:
            return int(sub)
    return None

def _foreground_with_attach(hwnd: int, focus_child: Optional[int] = None, timeout_ms: int = 2000) -> bool:
    if not DANGER:
        return False
    target = HWND(hwnd)
    user32.ShowWindow(target, SW_RESTORE)
    user32.BringWindowToTop(target)
    cur_thread = kernel32.GetCurrentThreadId()
    tgt_thread = user32.GetWindowThreadProcessId(target, None) or kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(cur_thread, tgt_thread, True)
    ok = bool(user32.SetForegroundWindow(target))
    if focus_child:
        user32.SetFocus(HWND(focus_child))
    user32.AttachThreadInput(cur_thread, tgt_thread, False)
    end = time.time() + (timeout_ms/1000.0)
    while time.time() < end:
        if int(user32.GetForegroundWindow() or 0) == hwnd:
            return True
        time.sleep(0.02)
    return ok

def _get_edit_text(h_edit: int) -> str:
    ln = int(user32.SendMessageW(HWND(h_edit), WM_GETTEXTLENGTH, 0, 0))
    buf = ctypes.create_unicode_buffer(ln + 1)
    user32.SendMessageW(HWND(h_edit), WM_GETTEXT, ln + 1, ctypes.cast(buf, LPARAM))
    return buf.value

def _set_edit_text(h_edit: int, text: str) -> None:
    user32.SendMessageW(HWND(h_edit), WM_SETTEXT, 0, ctypes.cast(ctypes.create_unicode_buffer(text), LPARAM))

def _copy_from_edit(h_edit: int) -> None:
    user32.SendMessageW(HWND(h_edit), WM_COPY, 0, 0)

def _paste_into_edit(h_edit: int) -> None:
    user32.SendMessageW(HWND(h_edit), WM_PASTE, 0, 0)

def focus_pid(pid: int) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    hwnd = _find_top_hwnd_for_pid(int(pid))
    if not hwnd:
        return {"ok": False, "error": f"no window for pid {pid}"}
    edit = _find_first_edit(hwnd)
    _foreground_with_attach(hwnd, focus_child=edit)
    return {"ok": True, "pid": int(pid), "hwnd": hwnd, "title": _get_title(hwnd), "has_edit": bool(edit)}

def get_text_pid(pid: int) -> Dict[str, Any]:
    hwnd = _find_top_hwnd_for_pid(int(pid))
    if not hwnd:
        return {"ok": False, "error": f"no window for pid {pid}"}
    edit = _find_first_edit(hwnd)
    if not edit:
        return {"ok": False, "error": "no edit control"}
    return {"ok": True, "pid": int(pid), "hwnd": hwnd, "text": _get_edit_text(edit)}

def set_text_pid(pid: int, text: str) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    hwnd = _find_top_hwnd_for_pid(int(pid))
    if not hwnd:
        return {"ok": False, "error": f"no window for pid {pid}"}
    edit = _find_first_edit(hwnd)
    if not edit:
        return {"ok": False, "error": "no edit control"}
    _foreground_with_attach(hwnd, focus_child=edit)
    _set_edit_text(edit, text)
    return {"ok": True, "pid": int(pid), "hwnd": hwnd, "len": len(text)}

def copy_pid(pid: int) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    hwnd = _find_top_hwnd_for_pid(int(pid))
    if not hwnd:
        return {"ok": False, "error": f"no window for pid {pid}"}
    edit = _find_first_edit(hwnd)
    if not edit:
        return {"ok": False, "error": "no edit control"}
    _foreground_with_attach(hwnd, focus_child=edit)
    _copy_from_edit(edit)
    return {"ok": True, "pid": int(pid), "hwnd": hwnd}

def paste_pid(pid: int) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    hwnd = _find_top_hwnd_for_pid(int(pid))
    if not hwnd:
        return {"ok": False, "error": f"no window for pid {pid}"}
    edit = _find_first_edit(hwnd)
    if not edit:
        return {"ok": False, "error": "no edit control"}
    _foreground_with_attach(hwnd, focus_child=edit)
    _paste_into_edit(edit)
    txt = _get_edit_text(edit)
    return {"ok": True, "pid": int(pid), "hwnd": hwnd, "text": txt}

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

def register(tools) -> None:
    tools.add("win.focus_pid",    focus_pid,    desc="Focus a window by process id and its edit control (if any)")
    tools.add("win.get_text_pid", get_text_pid, desc="Get text from a window's edit control by process id")
    tools.add("win.set_text_pid", set_text_pid, desc="Set/replace text in a window's edit control by process id")
    tools.add("win.copy_pid",     copy_pid,     desc="Copy (WM_COPY) in a window's edit control by process id")
    tools.add("win.paste_pid",    paste_pid,    desc="Paste (WM_PASTE) in a window's edit control by process id")
    tools.add("win.list_windows", list_windows, desc="List top-level windows with pid/title visibility filters")
    tools.add("win.count_windows", count_windows, desc="Count top-level windows (visible/titled filters)")
