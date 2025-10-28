# C:\bots\ecosys\tools\currency.py
from __future__ import annotations

from typing import Any, Dict, Optional
import json
import ssl
import urllib.request
import urllib.parse

API = "https://api.exchangerate.host/convert"
TIMEOUT = 20


def convert(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    try:
        params = {
            "from": (from_currency or "").upper(),
            "to": (to_currency or "").upper(),
            "amount": float(amount),
        }
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url=url, method="GET")
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            body = resp.read() if hasattr(resp, "read") else b""
        text = body.decode("utf-8", errors="replace")
        data = json.loads(text)
        if not isinstance(data, dict):
            return {"ok": False, "error": "bad response"}
        result = data.get("result")
        info = data.get("info", {}) if isinstance(data.get("info"), dict) else {}
        rate = info.get("rate")
        return {"ok": True, "amount": float(amount), "from": params["from"], "to": params["to"], "rate": rate, "result": result}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(reg) -> None:
    desc = "Convert currencies using exchangerate.host -> {ok,amount,from,to,rate,result}"
    reg.add("currency.convert", convert, desc=desc)
    reg.add("fx.convert", convert, desc=desc)
