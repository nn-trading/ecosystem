import os, json, time, ctypes
from mss import mss
from PIL import Image
from screeninfo import get_monitors
from .auto_utils import unique_path
import win32gui

def count_monitors():
    try:
        return {"monitors": len(get_monitors())}
    except Exception:
        return {"monitors": 1}

def _enum_windows():
    res=[]
    def cb(h, l):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowTextLength(h)>0:
            res.append(h)
        return True
    win32gui.EnumWindows(cb, None)
    return res

def count_windows():
    try:
        return {"windows": len(_enum_windows())}
    except Exception:
        return {"windows": 0}

def screenshot_autoname(root, stem='auto'):
    screens = os.path.join(root, 'reports','screens')
    os.makedirs(screens, exist_ok=True)
    path = unique_path(screens, stem, ".png")
    with mss() as sct:
        shot = sct.shot(output=path)
    return {"path": path}

def write_text_autoname(text):
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    path = unique_path(desktop, 'auto_probe', '.txt')
    with open(path, 'w', encoding='utf-8', errors='ignore') as f:
        f.write(text)
    return {"path": path}
