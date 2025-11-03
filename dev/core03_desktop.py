# dev/core03_desktop.py
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CFG  = ROOT/"config/core.yaml"
REPORTS = ROOT/"reports"

def load_cfg():
    import yaml
    return (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}) if CFG.exists() else {}

def write(p:Path, txt:str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")

def screenshot_safe(path:str)->tuple[bool,str]:
    try:
        import pyautogui
        img = pyautogui.screenshot()
        out = ROOT/path
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        return True, str(out)
    except Exception as e:
        return False, f"{e}"

def screen_info(path:str)->None:
    info={}
    try:
        import screeninfo
        info["monitors"]=[m.__dict__ for m in screeninfo.get_monitors()]
    except Exception as e:
        info["error"]=str(e)
    (ROOT/path).write_text(json.dumps(info, indent=2), encoding="utf-8")

def main():
    cfg=load_cfg()
    c3 = cfg.get("core03",{})
    if c3.get("screenshot_on_start", True):
        ok, msg = screenshot_safe(c3.get("screenshot_path","artifacts\\desktop_smoke.png"))
        write(REPORTS/"core03_screenshot_result.txt", f"ok={ok} path_or_err={msg}\n")
    screen_info(c3.get("screeninfo_json","reports\\screeninfo.json"))
    write(REPORTS/"core03_done.txt", f"ts={datetime.now():%Y-%m-%d %H:%M:%S}\n")

if __name__=="__main__":
    main()
