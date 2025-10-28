# C:\bots\ecosys\tools\currency.py
from __future__ import annotations

from typing import Any, Dict, Optional
import json
import ssl
import urllib.request
import urllib.parse

# Primary and fallback providers (no API key required)
API_PRIMARY = "https://api.exchangerate.host/convert"
API_FRANKFURTER = "https://api.frankfurter.app/latest"
TIMEOUT = 20


def _urlopen(url: str):
    req = urllib.request.Request(url=url, method="GET")
    ctx = ssl.create_default_context()
    return urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)


def _try_exchangerate_host(amount: float, base: str, quote: str) -> Optional[Dict[str, Any]]:
    params = {"from": base, "to": quote, "amount": float(amount)}
    url = API_PRIMARY + "?" + urllib.parse.urlencode(params)
    resp = _urlopen(url)
    try:
        body = resp.read() if hasattr(resp, "read") else b""
    finally:
        try:
            resp.close()
        except Exception:
            pass
    text = body.decode("utf-8", errors="replace")
    data = json.loads(text)
    if not isinstance(data, dict):
        return None
    result = data.get("result")
    info = data.get("info", {}) if isinstance(data.get("info"), dict) else {}
    rate = info.get("rate")
    if result is None or rate is None:
        return None
    return {
        "ok": True,
        "provider": "exchangerate.host",
        "amount": float(amount),
        "from": base,
        "to": quote,
        "rate": rate,
        "result": result,
        "url": url,
    }


def _try_frankfurter(amount: float, base: str, quote: str) -> Optional[Dict[str, Any]]:
    # Frankfurter returns rates for the specified base; with amount it returns converted amount in rates[quote]
    q = {"amount": float(amount), "from": base, "to": quote}
    url = API_FRANKFURTER + "?" + urllib.parse.urlencode(q)
    resp = _urlopen(url)
    try:
        body = resp.read() if hasattr(resp, "read") else b""
    finally:
        try:
            resp.close()
        except Exception:
            pass
    text = body.decode("utf-8", errors="replace")
    data = json.loads(text)
    if not isinstance(data, dict):
        return None
    rates = data.get("rates") if isinstance(data.get("rates"), dict) else None
    if not rates or quote not in rates:
        return None
    result = float(rates[quote])
    amt = float(amount) if amount is not None else 1.0
    rate = (result / amt) if amt else None
    if rate is None:
        return None
    return {
        "ok": True,
        "provider": "frankfurter.app",
        "amount": amt,
        "from": base,
        "to": quote,
        "rate": rate,
        "result": result,
        "url": url,
    }


def convert(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    try:
        base = (from_currency or "").upper()
        quote = (to_currency or "").upper()
        amt = float(amount)
        # Try primary provider
        try:
            res = _try_exchangerate_host(amt, base, quote)
            if res:
                return res
        except Exception:
            # ignore and fall back
            pass
        # Fallback to Frankfurter
        try:
            res2 = _try_frankfurter(amt, base, quote)
            if res2:
                return res2
        except Exception:
            pass
        return {"ok": False, "error": "conversion_failed"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(reg) -> None:
    desc = "Convert currencies (exchangerate.host -> frankfurter.app fallback) -> {ok,amount,from,to,rate,result,provider,url}"
    reg.add("currency.convert", convert, desc=desc)
    reg.add("fx.convert", convert, desc=desc)
