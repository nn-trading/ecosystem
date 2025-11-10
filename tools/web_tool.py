import argparse, os, sys, json, time
from pathlib import Path

def _ensure_dir(p):
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)

def cmd_get(args):
    try:
        import requests
    except Exception as e:
        return {"ok": False, "error": f"missing requests: {e}"}
    headers = {}
    if args.headers:
        try:
            headers = json.loads(args.headers)
        except Exception as e:
            return {"ok": False, "error": f"bad headers json: {e}"}
    try:
        r = requests.get(args.url, headers=headers, timeout=30)
        out = {"ok": True, "status": r.status_code}
        if args.save:
            _ensure_dir(args.save)
            with open(args.save, 'wb') as f:
                f.write(r.content)
            out["path"] = args.save
            out["len"] = len(r.content)
        else:
            text = r.text
            out["text_snippet"] = text[:1000]
            out["len"] = len(text)
        return out
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _try_clicks_in_frame(frame, texts, selectors, timeout_ms, clicked):
    # try role=button by name, then text, then selector css
    for txt in texts or []:
        try:
            frame.get_by_role("button", name=txt, exact=False).click(timeout=timeout_ms)
            clicked.append({"by":"role","value":txt})
            time.sleep(0.25)
            return True
        except Exception:
            pass
        try:
            frame.get_by_text(txt, exact=False).click(timeout=timeout_ms)
            clicked.append({"by":"text","value":txt})
            time.sleep(0.25)
            return True
        except Exception:
            pass
    for sel in selectors or []:
        try:
            frame.click(sel, timeout=timeout_ms)
            clicked.append({"by":"selector","value":sel})
            time.sleep(0.25)
            return True
        except Exception:
            pass
        try:
            frame.locator(sel).first.click(timeout=timeout_ms)
            clicked.append({"by":"locator","value":sel})
            time.sleep(0.25)
            return True
        except Exception:
            pass
    return False

def _try_clicks_all_frames(page, texts, selectors, timeout_ms=5000):
    clicked=[]
    # include main frame and all frames
    frames = [page.main_frame] + [f for f in page.frames if f is not page.main_frame]
    for fr in frames:
        if _try_clicks_in_frame(fr, texts, selectors, timeout_ms, clicked):
            return True, clicked
    return False, clicked

def cmd_play(args):
    try:
        from playwright.sync_api import sync_playwright
        from urllib.parse import urlparse
    except Exception as e:
        return {"ok": False, "error": f"missing deps: {e}"}
    wait_ms = None
    if args.timeout is not None:
        try:
            wait_ms = max(0, int(args.timeout) * 1000)
        except Exception:
            wait_ms = 0

    # build consent candidates
    auto_texts = []
    auto_selectors = []
    try:
        host = urlparse(args.url).netloc.lower()
    except Exception:
        host = ""
    if args.auto_consent:
        if "google." in host:
            auto_texts = ["I agree","Accept all","Yes, Im in","Agree to the use of cookies"]
            auto_selectors = [
                "button[aria-label='Accept all']",
                "#L2AGLb",
                "form[action*='consent'] button[type='submit']"
            ]

    texts = list(args.click_text or []) + auto_texts
    selectors = list(args.click_selector or []) + auto_selectors

    out = {"ok": True, "mode": "play", "url": args.url}
    clicked = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(args.url, wait_until='load', timeout=60000)
            if args.wait_selector:
                page.wait_for_selector(args.wait_selector, timeout=wait_ms or 30000)

            if texts or selectors:
                _, clicked = _try_clicks_all_frames(page, texts, selectors, timeout_ms=5000)

            if args.page_shot:
                _ensure_dir(args.page_shot)
                page.screenshot(path=args.page_shot, full_page=bool(args.fullpage))
                out["page_shot"] = args.page_shot
                out["fullpage"] = bool(args.fullpage)
            if args.html_out:
                _ensure_dir(args.html_out)
                html = page.content()
                with open(args.html_out, 'w', encoding='utf-8') as f:
                    f.write(html)
                out["html_out"] = args.html_out
                out["html_len"] = len(html)
            if args.eval_selector:
                try:
                    val = page.eval_on_selector(args.eval_selector, "el => el.innerText")
                    out["eval_selector"] = args.eval_selector
                    out["text"] = val
                except Exception as e:
                    out["eval_error"] = str(e)
        except Exception as e:
            return {"ok": False, "error": str(e), "clicked": clicked}
        finally:
            try: browser.close()
            except: pass

    out["clicked"] = clicked
    return out

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    g = sub.add_parser('get')
    g.add_argument('--url', required=True)
    g.add_argument('--headers')
    g.add_argument('--save')
    g.set_defaults(func=cmd_get)

    p = sub.add_parser('play')
    p.add_argument('--url', required=True)
    p.add_argument('--wait-selector')
    p.add_argument('--timeout', type=int)           # seconds
    p.add_argument('--page-shot')
    p.add_argument('--fullpage', action='store_true')
    p.add_argument('--html-out')
    p.add_argument('--eval-selector')
    p.add_argument('--click-text', action='append')      # may repeat
    p.add_argument('--click-selector', action='append')  # may repeat
    p.add_argument('--auto-consent', action='store_true')
    p.set_defaults(func=cmd_play)

    args = ap.parse_args()
    try:
        res = args.func(args)
    except Exception as e:
        res = {"ok": False, "error": str(e)}
    print(json.dumps(res, ensure_ascii=False))

if __name__ == '__main__':
    main()
