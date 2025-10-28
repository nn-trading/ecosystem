# C:\bots\ecosys\tools\http.py
from __future__ import annotations

import json, time
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


def _encode_body(data: Optional[Any], json_body: Optional[Any], headers: Optional[Dict[str, str]] = None) -> tuple[bytes, Dict[str, str]]:
    hdrs = dict(headers or {})
    if json_body is not None:
        payload = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json; charset=utf-8")
        return payload, hdrs
    if isinstance(data, (bytes, bytearray)):
        return bytes(data), hdrs
    if isinstance(data, str):
        hdrs.setdefault("Content-Type", "text/plain; charset=utf-8")
        return data.encode("utf-8"), hdrs
    if isinstance(data, dict):
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
        return urllib.parse.urlencode(data, doseq=True).encode("utf-8"), hdrs
    return b"", hdrs


def fetch(method: str, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, json_body: Optional[Any] = None, data: Optional[Any] = None, timeout: Optional[int] = None, retries: int = 2, backoff: float = 0.5) -> Dict[str, Any]:
    try:
        m = (method or "GET").upper()
        q = urllib.parse.urlencode(params or {}, doseq=True)
        full = f"{url}{'&' if '?' in url else '?'}{q}" if q else url
        body, hdrs = _encode_body(data, json_body, headers)
        req = _mk_req(full, m, headers=hdrs, data=(body if m != "GET" else None))
        ctx = ssl.create_default_context()
        last_err: Optional[str] = None
        for attempt in range(max(1, int(retries)) + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout or _DEF_TIMEOUT, context=ctx) as resp:
                    status, rh, rb = _read_response(resp)
                text = rb.decode("utf-8", errors="replace")
                return {"ok": 200 <= status < 300, "status": status, "headers": rh, "url": full, "text": text, "json": _json_try(text), "provider": "urllib"}
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                if attempt < retries:
                    time.sleep(backoff * (2 ** attempt))
                else:
                    break
        return {"ok": False, "error": last_err or "request_failed", "url": full}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "url": url}


def http_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    return fetch("GET", url, params=params, headers=headers, timeout=timeout)


def http_post(url: str, data: Optional[Any] = None, json_body: Optional[Any] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    return fetch("POST", url, headers=headers, data=data, json_body=json_body, timeout=timeout)


def register(reg) -> None:
    reg.add("http.get", http_get, desc="HTTP GET (urllib) -> {ok,status,headers,url,text,json?}")
    reg.add("http.post", http_post, desc="HTTP POST (urllib) -> {ok,status,headers,url,text,json?}")
    reg.add("http.fetch", fetch, desc="HTTP fetch with retries/backoff -> {ok,status?,headers?,url,text?,json?,provider}")
