# C:\bots\ecosys\tools\weather.py
from __future__ import annotations

import os, re, urllib.parse
from typing import Any, Dict, Optional

try:
    import json
except Exception:
    json = None  # type: ignore

from .http import http_get

# Free endpoints (no key) used as defaults; can be overridden via env vars
DEFAULT_WEATHER_URL = os.environ.get("WEATHER_URL", "https://wttr.in/")
DEFAULT_IPINFO_URL = os.environ.get("IPINFO_URL", "https://ipinfo.io/json")

# Additional fallback mirrors/providers (best-effort)
_FALLBACK_WEATHER_BASES = [
    "https://v2.wttr.in",
    "http://wttr.in",
]

_PUNCT = ",.!?:;\"'()[]{}"

def _clean_city(s: str) -> str:
    s = (s or "").strip()
    s = s.strip(_PUNCT + " ")
    s = re.sub(r"\s+", " ", s)
    return s


def _detect_city_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.strip()
    # Trim trailing filler like 'right now' / 'now' / 'today' / 'currently'
    t = re.sub(r"\b(right\s+now|now|currently|today)\b[?.!]*$", "", t, flags=re.IGNORECASE).strip()
    # Prefer pattern: 'in <city>' but stop before filler/punctuation/end; use non-greedy capture and don't eat 'for N days'
    m = re.search(r"\bin\s+([A-Za-z][A-Za-z .\-']+?)(?=\s*(?:for\s+\d+\s+days?\b|right\s+now|now|currently|today)\b|[?.!]|$)", t, flags=re.IGNORECASE)
    if m:
        return _clean_city(m.group(1))
    # Fallback: 'in <city>' to end
    m2 = re.search(r"\bin\s+([A-Za-z][A-Za-z .\-']+)$", t, flags=re.IGNORECASE)
    if m2:
        return _clean_city(m2.group(1))
    # Fallback: last token/phrase with letters (ignore filler like 'now')
    parts = [p.strip(_PUNCT + " ") for p in t.split() if any(c.isalpha() for c in p)]
    stop = {"now","today","currently","right","rightnow","weather"}
    while parts and parts[-1].lower() in stop:
        parts.pop()
    if parts:
        return _clean_city(parts[-1])
    return None


def _normalize_wttr(data: Any) -> Dict[str, Any]:
    norm: Dict[str, Any] = {}
    try:
        if isinstance(data, dict):
            cc = data.get("current_condition")
            if isinstance(cc, list) and cc:
                cur = cc[0] if isinstance(cc[0], dict) else None
                if isinstance(cur, dict):
                    t = cur.get("temp_C")
                    try:
                        norm["temp_c"] = float(t)
                    except Exception:
                        pass
                    wd = cur.get("weatherDesc")
                    if isinstance(wd, list) and wd and isinstance(wd[0], dict):
                        desc = wd[0].get("value")
                        if isinstance(desc, str):
                            norm["condition"] = desc
    except Exception:
        pass
    return norm


def weather_get(text: Optional[str] = None, city: Optional[str] = None, fmt: str = "j1") -> Dict[str, Any]:
    """
    Fetch current weather using wttr.in with fallback mirrors.
    - text: a natural phrase like "weather in Dublin" (used to guess city)
    - city: explicit city name overrides text parsing
    - fmt: wttr.in format; 'j1' returns JSON
    Returns: {ok, city, url, data?, provider?, norm?, error?}
    """
    try:
        c = _clean_city((city or _detect_city_from_text(text or "") or ""))
        if not c:
            # Try to geolocate via IP to get a default city
            ip = http_get(DEFAULT_IPINFO_URL)
            if ip.get("ok") and isinstance(ip.get("json"), dict):
                c = _clean_city(ip["json"].get("city") or "")
        if not c:
            return {"ok": False, "error": "no city specified or detected"}

        path_city = urllib.parse.quote(c)
        bases = [DEFAULT_WEATHER_URL.rstrip("/")] + [b.rstrip("/") for b in _FALLBACK_WEATHER_BASES if b]
        seen = []
        for base in bases:
            if base in seen:
                continue
            seen.append(base)
            url = f"{base}/{path_city}?format={fmt}"
            res = http_get(url)
            if res.get("ok"):
                data = res.get("json") or res.get("text")
                out = {"ok": True, "city": c, "url": url, "data": data, "provider": base}
                if fmt == "j1" and data is not None:
                    out["norm"] = _normalize_wttr(data)
                return out
        # If none succeeded, return last error if available
        return {"ok": False, "error": "weather_request_failed"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(reg) -> None:
    reg.add("weather.get", weather_get, desc="Fetch weather (wttr.in) with fallback. Args: text?, city?, fmt='j1'.")
