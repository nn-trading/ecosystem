import os, json, time, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RPTS=ROOT/"reports"; CHAT=RPTS/"chat"; SCRN=RPTS/"screens"; DESK=Path(os.path.expanduser("~"))/"Desktop"
RPTS.mkdir(parents=True, exist_ok=True); CHAT.mkdir(parents=True, exist_ok=True); SCRN.mkdir(parents=True, exist_ok=True)
res={"ok": True, "errors": [], "artifacts": {}}
def err(m): res["errors"].append(str(m)); res["ok"]=False

# monitors/windows
def count_monitors():
    try:
        from screeninfo import get_monitors
        return {"monitors": len(get_monitors())}
    except Exception as e:
        return {"monitors": 0}
def count_windows():
    try:
        import win32gui
        def ok(h):
            try: return win32gui.IsWindowVisible(h) and win32gui.GetWindowTextLength(h)>0
            except: return False
        n=0
        def enum(h,l):
            nonlocal n
            if ok(h): n+=1
            return True
        win32gui.EnumWindows(enum,None)
        return {"windows": n}
    except Exception:
        return {"windows": 0}

# screenshot
def screenshot(prefix="e2e"):
    try:
        import mss
        ts=time.strftime("%Y%m%d_%H%M%S"); p=SCRN/f"{prefix}_{ts}.png"
        with mss.mss() as s: s.shot(output=str(p))
        return str(p)
    except Exception as e:
        err(f"screenshot:{e}"); return None

# desktop write
try:
    (DESK/"e2e_probe.txt").write_text("OK", encoding="utf-8")
    res["artifacts"]["desktop_write"]=str(DESK/"e2e_probe.txt")
except Exception as e:
    err(f"desktop_write:{e}")

# optional notepad automation (best-effort)
try:
    import pyautogui, time as _t
    p = subprocess.Popen(["notepad.exe"])
    _t.sleep(1.5)
    pyautogui.typewrite("E2E NOTEPAD OK", interval=0.02)
    pyautogui.hotkey("ctrl","s"); _t.sleep(0.8)
    save_path = str(DESK/"e2e_notepad.txt")
    pyautogui.typewrite(save_path, interval=0.01); _t.sleep(0.4)
    pyautogui.press("enter"); _t.sleep(0.6)
    res["artifacts"]["notepad_saved"]=save_path
    try: p.terminate()
    except: pass
except Exception as e:
    # not critical; record and continue
    res["artifacts"]["notepad_saved"]=False
    res["errors"].append(f"notepad:{e}")

# OpenAI ping (uses env or api_key.txt)
key=os.environ.get("OPENAI_API_KEY","") or (ROOT/"api_key.txt").read_text().strip() if (ROOT/"api_key.txt").exists() else ""
if key:
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)
        r=client.chat.completions.create(model="gpt-5", messages=[{"role":"user","content":"ping"}], max_completion_tokens=4)
        res["artifacts"]["openai_ok"]=True
    except Exception as e:
        res["artifacts"]["openai_ok"]=False; err(f"openai:{e}")
else:
    res["artifacts"]["openai_ok"]=False

res["artifacts"]["monitors"]=count_monitors()
res["artifacts"]["windows"]=count_windows()
res["artifacts"]["screenshot"]=screenshot("e2e")
(RPTS/"E2E_RESULT.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res))
