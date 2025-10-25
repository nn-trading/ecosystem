# C:\bots\ecosys\tools\http.py
from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

_DEF_TIMEOUT = 20


def _mk_req(url: str, method: str, headers: Optional[Dict[str, str]] = None, data: Optional[bytes] = None):
    req = urllib.request.Request(url=url, method=method.upper())
    if headers:
        for k, v in headers.items():
            if v is not None:
                req.add_header(str(k), str(v))
    if data is not None:
        req.data = data
    return req


def _read_response(resp) -> Tuple[int, Dict[str, str], bytes]:
    status = getattr(resp, "status", None)
    if status is None:
        status = getattr(resp, "code", None)
    try:
        hdrs = {k: v for k, v in resp.headers.items()} if hasattr(resp, "headers") else {}
    except Exception:
        hdrs = {}
    body = resp.read() if hasattr(resp, "read") else b""
    return int(status or 0), hdrs, body


def _json_try(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        return None


def http_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    try:
        q = urllib.parse.urlencode(params or {}, doseq=True)
        full = f"{url}{'&' if '?' in url else '?'}{q}" if q else url
        req = _mk_req(full, "GET", headers=headers)
        # Relax SSL to avoid local cert issues; callers should use HTTPS endpoints
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout or _DEF_TIMEOUT, context=ctx) as resp:
            status, hdrs, body = _read_response(resp)
        text = body.decode("utf-8", errors="replace")
        return {"ok": 200 <= status < 300, "status": status, "headers": hdrs, "url": full, "text": text, "json": _json_try(text)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "url": url}


def http_post(url: str, data: Optional[Any] = None, json_body: Optional[Any] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    try:
        hdrs = dict(headers or {})
        payload: bytes
        if json_body is not None:
            payload = json.dumps(json_body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json; charset=utf-8")
        elif isinstance(data, (bytes, bytearray)):
            payload = bytes(data)
        elif isinstance(data, str):
            payload = data.encode("utf-8")
            hdrs.setdefault("Content-Type", "text/plain; charset=utf-8")
        elif isinstance(data, dict):
            payload = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
        else:
            payload = b""
        req = _mk_req(url, "POST", headers=hdrs, data=payload)
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout or _DEF_TIMEOUT, context=ctx) as resp:
            status, rh, body = _read_response(resp)
        text = body.decode("utf-8", errors="replace")
        return {"ok": 200 <= status < 300, "status": status, "headers": rh, "url": url, "text": text, "json": _json_try(text)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "url": url}


def register(reg) -> None:
    reg.add("http.get", http_get, desc="HTTP GET (urllib) -> {ok,status,headers,url,text,json?}")
    reg.add("http.post", http_post, desc="HTTP POST (urllib) -> {ok,status,headers,url,text,json?}")
