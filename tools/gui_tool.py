import argparse, sys, time, os, json
try:
    import pyautogui, mouse, mss
    from PIL import Image
    import pygetwindow as gw
    import pytesseract
except Exception as e:
    print(json.dumps({"ok": False, "error": f"missing deps: {e}"})); sys.exit(1)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# Try to auto-locate Tesseract on Windows
if os.name == "nt":
    tpath = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    if os.path.exists(tpath):
        try:
            pytesseract.pytesseract.tesseract_cmd = tpath
        except Exception:
            pass

def do_move(args):
    x, y = int(args.x), int(args.y)
    dur = float(args.duration or 0)
    if args.relative:
        pyautogui.moveRel(x, y, duration=dur)
    else:
        pyautogui.moveTo(x, y, duration=dur)
    return {"ok": True, "action":"move","x":x,"y":y,"relative":bool(args.relative)}

def do_click(args):
    btn = (args.button or "left").lower()
    dur = float(args.duration or 0)
    if args.x is not None and args.y is not None:
        pyautogui.moveTo(int(args.x), int(args.y), duration=dur)
    if args.double:
        pyautogui.click(button=btn, clicks=2, interval=0.1)
    else:
        pyautogui.click(button=btn)
    return {"ok": True, "action":"click","button":btn,"x":args.x,"y":args.y,"double":bool(args.double)}

def do_type(args):
    txt = args.text or ""
    delay = float(args.delay or 0.01)
    pyautogui.write(txt, interval=delay)
    if args.enter:
        pyautogui.press("enter")
    return {"ok": True, "action":"type","len":len(txt),"enter":bool(args.enter)}

def do_hotkey(args):
    keys=[k.strip() for k in (args.keys or "").split(",") if k.strip()]
    if not keys: return {"ok":False,"error":"no keys"}
    pyautogui.hotkey(*keys)
    return {"ok": True, "action":"hotkey","keys":keys}

def do_scroll(args):
    amt = int(args.amount)
    pyautogui.scroll(amt)
    return {"ok": True, "action":"scroll","amount":amt}

def do_screenshot(args):
    # monitor index per mss:
    #   0 = virtual/full desktop (all monitors)
    #   1 = primary monitor, 2 = second, etc.
    path = args.path or os.path.join(r"C:\\bots\\ecosys\\reports\\screens", f"shot_{int(time.time())}.png")
    try:
        mon = int(args.monitor)
    except Exception:
        mon = 0
    with mss.mss() as s:
        mons = s.monitors
        if mon < 0 or mon >= len(mons):
            mon = 0
        sshot = s.grab(mons[mon])
        img = Image.frombytes("RGB", sshot.size, sshot.bgra, "raw", "BGRX")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path)
    return {"ok": True, "action":"screenshot","path":path,"monitor":mon}

def do_ocr(args):
    if not os.path.exists(args.image):
        return {"ok": False, "error":"image not found"}
    try:
        txt = pytesseract.image_to_string(Image.open(args.image))
    except Exception as e:
        return {"ok": False, "error": f"ocr error: {e}"}
    return {"ok": True, "action":"ocr","text":txt}

def do_window(args):
    title=args.title or ""
    wins=gw.getWindowsWithTitle(title)
    if not wins: return {"ok":False,"error":"window not found"}
    w=wins[0]
    try:
        w.activate()
        return {"ok":True,"action":"window","title":w.title}
    except Exception as e:
        return {"ok":False,"error":str(e)}

def do_openurl(args):
    # Open via Playwright Chromium (headless=False)
    # If --timeout > 0, keep window open for that many seconds before returning.
    # If --keep-open, default to 60s unless a --timeout is provided.
    # If --page-shot is provided, take a Playwright page screenshot before returning (works even if window closes later).
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return {"ok":False,"error":f"playwright not installed: {e}"}
    timeout_s = int(args.timeout) if args.timeout is not None else 0
    if args.keep_open and timeout_s <= 0:
        timeout_s = 60
    page_shot = args.page_shot
    fullpage  = bool(args.fullpage)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(args.url, wait_until="load", timeout=60000)
        if page_shot:
            try:
                os.makedirs(os.path.dirname(page_shot), exist_ok=True)
                page.screenshot(path=page_shot, full_page=fullpage)
            except Exception as e:
                return {"ok": False, "error": f"page screenshot failed: {e}"}
        if timeout_s > 0:
            try:
                time.sleep(timeout_s)
            except KeyboardInterrupt:
                pass
        return {"ok":True,"action":"openurl","url":args.url,"kept_open_seconds":timeout_s, "page_shot": page_shot, "fullpage": fullpage}

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd", required=True)

    m=sub.add_parser("move"); m.add_argument("--x", required=True); m.add_argument("--y", required=True); m.add_argument("--relative", action="store_true"); m.add_argument("--duration"); m.set_defaults(func=do_move)
    c=sub.add_parser("click"); c.add_argument("--x"); c.add_argument("--y"); c.add_argument("--duration"); c.add_argument("--button", default="left"); c.add_argument("--double", action="store_true"); c.set_defaults(func=do_click)
    t=sub.add_parser("type"); t.add_argument("--text", required=True); t.add_argument("--delay"); t.add_argument("--enter", action="store_true"); t.set_defaults(func=do_type)
    h=sub.add_parser("hotkey"); h.add_argument("--keys", required=True, help="comma-separated, e.g. ctrl,shift,esc"); h.set_defaults(func=do_hotkey)
    sc=sub.add_parser("scroll"); sc.add_argument("--amount", required=True); sc.set_defaults(func=do_scroll)
    s=sub.add_parser("screenshot"); s.add_argument("--path"); s.add_argument("--monitor", type=int, default=0); s.set_defaults(func=do_screenshot)
    o=sub.add_parser("ocr"); o.add_argument("--image", required=True); o.set_defaults(func=do_ocr)
    w=sub.add_parser("window"); w.add_argument("--title", required=True); w.set_defaults(func=do_window)
    u=sub.add_parser("openurl"); u.add_argument("--url", required=True); u.add_argument("--timeout", type=int, default=0); u.add_argument("--keep-open", action="store_true"); u.add_argument("--page-shot"); u.add_argument("--fullpage", action="store_true"); u.set_defaults(func=do_openurl)

    args=ap.parse_args()
    try:
        res=args.func(args)
    except Exception as e:
        res={"ok":False,"error":str(e)}
    print(json.dumps(res, ensure_ascii=False))

if __name__=="__main__":
    main()


def wait_title_contains(substring: str, timeout_sec: int = 15, poll_ms: int = 200) -> dict:
    """
    Thin wrapper over core.win_wait.wait_title_contains.
    Returns a dict with keys: ok (bool), title (str), contains (str), and timing fields.
    """
    try:
        from core.win_wait import wait_title_contains as _w
    except Exception as e:
        return {"ok": False, "error": f"import core.win_wait failed: {e}"}
    return _w(substring, timeout_sec, poll_ms)
