# C:\bots\ecosys\tools\webfetch.py
from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

_DEF_TIMEOUT = 25


def fetch_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    try:
        q = urllib.parse.urlencode(params or {}, doseq=True)
        full = f"{url}{'&' if '?' in url else '?'}{q}" if q else url
        req = urllib.request.Request(url=full, method="GET")
        if headers:
            for k, v in headers.items():
                if v is not None:
                    req.add_header(str(k), str(v))
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout or _DEF_TIMEOUT, context=ctx) as resp:
            body = resp.read() if hasattr(resp, "read") else b""
        text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except Exception:
            return {"ok": False, "error": "response not JSON", "url": full, "text": text[:2000]}
        return {"ok": True, "url": full, "json": data}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "url": url}


def fetch_text(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    try:
        q = urllib.parse.urlencode(params or {}, doseq=True)
        full = f"{url}{'&' if '?' in url else '?'}{q}" if q else url
        req = urllib.request.Request(url=full, method="GET")
        if headers:
            for k, v in headers.items():
                if v is not None:
                    req.add_header(str(k), str(v))
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout or _DEF_TIMEOUT, context=ctx) as resp:
            body = resp.read() if hasattr(resp, "read") else b""
        text = body.decode("utf-8", errors="replace")
        return {"ok": True, "url": full, "text": text}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "url": url}


def register(reg) -> None:
    reg.add("web.fetch_json", fetch_json, desc="Fetch a URL and parse JSON -> {ok,url,json|error}")
    reg.add("web.fetch_text", fetch_text, desc="Fetch a URL and return text -> {ok,url,text|error}")
