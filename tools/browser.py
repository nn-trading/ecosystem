# C:\bots\ecosys\tools\browser.py
from __future__ import annotations

import os, tempfile, time, threading
from typing import Optional, Dict, Any

# Globals (for multi-step sessions, if you still want them)
_pw = None          # playwright object from sync_playwright().start()
_browser = None     # Browser
_context = None     # BrowserContext
_page = None        # Page
_owner_tid: Optional[int] = None

def _danger_ok() -> bool:
    return os.environ.get("AGENT_DANGER_MODE", "0") == "1"

def _start_in_this_thread(headless: bool = True):
    """
    Start Playwright in the CURRENT thread and keep handles.
    If already started in a different thread, close & re-start here.
    """
    global _pw, _browser, _context, _page, _owner_tid
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("playwright not installed. Run: pip install playwright && python -m playwright install chromium") from e

    me = threading.get_ident()
    if _owner_tid is not None and _owner_tid != me:
        # different thread => close previous session first
        close()

    if _page is not None and _owner_tid == me:
        return  # already running in this thread

    _pw = sync_playwright().start()
    _browser = _pw.chromium.launch(headless=headless)
    _context = _browser.new_context()
    _page = _context.new_page()
    _owner_tid = me

def launch(headless: bool = True) -> Dict[str, Any]:
    """
    Launch Chromium via Playwright (idempotent per thread).
    """
    _start_in_this_thread(headless=headless)
    return {"ok": True, "headless": headless}

def goto(url: str, wait: str = "load", headless: Optional[bool] = None) -> Dict[str, Any]:
    """
    Navigate to a URL (requires AGENT_DANGER_MODE=1). Works across steps by
    re-binding the session to the current thread if necessary.
    """
    if not _danger_ok():
        return {"ok": False, "error": "dangerous op blocked; set AGENT_DANGER_MODE=1"}
    _start_in_this_thread(headless=True if headless is None else headless)
    _page.goto(url, wait_until=wait)
    return {"ok": True, "url": url, "wait": wait}

def click(selector: str, delay_ms: int = 0) -> Dict[str, Any]:
    if not _danger_ok():
        return {"ok": False, "error": "dangerous op blocked; set AGENT_DANGER_MODE=1"}
    if _page is None:
        return {"ok": False, "error": "no page; call browser.goto first"}
    _page.click(selector)
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)
    return {"ok": True, "selector": selector}

def fill(selector: str, text: str, delay_ms: int = 0, clear: bool = True) -> Dict[str, Any]:
    if not _danger_ok():
        return {"ok": False, "error": "dangerous op blocked; set AGENT_DANGER_MODE=1"}
    if _page is None:
        return {"ok": False, "error": "no page; call browser.goto first"}
    if clear:
        _page.fill(selector, text)
    else:
        _page.type(selector, text)
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)
    return {"ok": True, "selector": selector, "len": len(text)}

def text(selector: str, timeout_ms: int = 5000) -> Dict[str, Any]:
    if _page is None:
        return {"ok": False, "error": "no page; call browser.goto first"}
    el = _page.locator(selector).first
    el.wait_for(timeout=timeout_ms)
    val = el.inner_text()
    return {"ok": True, "selector": selector, "text": val}

def screenshot(path: Optional[str] = None, full_page: bool = True) -> Dict[str, Any]:
    if _page is None:
        return {"ok": False, "error": "no page; call browser.goto first"}
    if not path:
        fd, tmp = tempfile.mkstemp(prefix="browser_", suffix=".png")
        os.close(fd); path = tmp
    # Enforce ASCII-only on the final filename component
    try:
        from core.pathutil import sanitize_save_path
        path, sanitized = sanitize_save_path(path)
    except Exception:
        sanitized = False
    _page.screenshot(path=path, full_page=full_page)
    return {"ok": True, "path": path, "full_page": full_page, "sanitized": sanitized}

def close() -> Dict[str, Any]:
    global _pw, _browser, _context, _page, _owner_tid
    try:
        if _page: _page.close()
    except Exception:
        pass
    try:
        if _context: _context.close()
    except Exception:
        pass
    try:
        if _browser: _browser.close()
    except Exception:
        pass
    try:
        if _pw: _pw.stop()
    except Exception:
        pass
    _pw = _browser = _context = _page = None
    _owner_tid = None
    return {"ok": True}

# ---------- One-shot helper that avoids thread issues entirely ----------
def snap(url: str, wait: str = "load", headless: bool = True, full_page: bool = True) -> Dict[str, Any]:
    """
    Open Chromium, go to URL, take screenshot, close everything.
    All in a single call → no cross-thread state.
    """
    if not _danger_ok():
        return {"ok": False, "error": "dangerous op blocked; set AGENT_DANGER_MODE=1"}
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return {"ok": False, "error": f"playwright missing: {e}. Run: pip install playwright && python -m playwright install chromium"}
    try:
        import tempfile, os
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until=wait)
            fd, tmp = tempfile.mkstemp(prefix="snap_", suffix=".png")
            os.close(fd)
            page.screenshot(path=tmp, full_page=full_page)
            context.close()
            browser.close()
        return {"ok": True, "url": url, "path": tmp, "full_page": full_page}
    except Exception as e:
        return {"ok": False, "error": f"browser.snap failed: {e}"}


def register(reg) -> None:
    reg.add("browser.launch", launch, desc="Launch Chromium via Playwright (idempotent per thread)")
    reg.add("browser.goto", goto, desc="Navigate to a URL using Playwright")
    reg.add("browser.click", click, desc="Click a selector")
    reg.add("browser.fill", fill, desc="Fill or type into a selector")
    reg.add("browser.text", text, desc="Get inner text of selector")
    reg.add("browser.screenshot", screenshot, desc="Take a screenshot of the current page")
    reg.add("browser.close", close, desc="Close Playwright browser and cleanup")
    reg.add("browser.snap", snap, desc="One-shot: open url, screenshot, close")
