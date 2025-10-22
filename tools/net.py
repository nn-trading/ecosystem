# C:\bots\ecosys\tools\net.py  (or netutil.py, depending on your tree)
from __future__ import annotations

import urllib.request
import urllib.error
import ssl
import os
from typing import Dict, Any, Optional, Tuple

def _make_request(url: str, headers: Optional[dict] = None) -> urllib.request.Request:
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    return req

def http_get(url: str,
             path: Optional[str] = None,
             headers: Optional[dict] = None,
             timeout: int = 60,
             verify_tls: bool = True) -> Dict[str, Any]:
    """
    GET a URL.
    - If 'path' is provided, save bytes to that file and return the path.
    - Otherwise return the response bytes and a utf-8 text preview.
    """
    try:
        ctx = None if verify_tls else ssl._create_unverified_context()
        req = _make_request(url, headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data: bytes = resp.read()
            status = resp.getcode()
            info = dict(resp.headers.items())

        saved = False
        out_path = None
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            saved = True
            out_path = path

        # Light preview (never huge)
        preview = None
        try:
            preview = data[:4096].decode("utf-8", errors="replace")
        except Exception:
            preview = None

        return {
            "ok": True,
            "status": status,
            "headers": info,
            "saved": saved,
            "path": out_path,
            "bytes": len(data),
            "preview": preview if not saved else None
        }
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTPError {e.code}: {e.reason}", "status": getattr(e, "code", None)}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": f"GET failed: {e}"}

def http_post(url: str,
              data: Optional[bytes] = None,
              headers: Optional[dict] = None,
              timeout: int = 60,
              verify_tls: bool = True) -> Dict[str, Any]:
    """
    Basic POST (bytes body). Returns status + preview text.
    """
    try:
        ctx = None if verify_tls else ssl._create_unverified_context()
        req = _make_request(url, headers)
        with urllib.request.urlopen(req, data=data, timeout=timeout, context=ctx) as resp:
            out: bytes = resp.read()
            status = resp.getcode()
            info = dict(resp.headers.items())
        preview = None
        try:
            preview = out[:4096].decode("utf-8", errors="replace")
        except Exception:
            preview = None
        return {"ok": True, "status": status, "headers": info, "bytes": len(out), "preview": preview}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTPError {e.code}: {e.reason}", "status": getattr(e, "code", None)}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": f"POST failed: {e}"}
