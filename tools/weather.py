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
    # Prefer pattern: 'in <city>' near the end
    m = re.search(r"\bin\s+([A-Za-z][A-Za-z .\-']+)$", t, flags=re.IGNORECASE)
    if m:
        return _clean_city(m.group(1))
    # Fallback: last token/phrase with letters
    parts = [p.strip(_PUNCT + " ") for p in t.split() if any(c.isalpha() for c in p)]
    if parts:
        return _clean_city(parts[-1])
    return None


def weather_get(text: Optional[str] = None, city: Optional[str] = None, fmt: str = "j1") -> Dict[str, Any]:
    """
    Fetch current weather using wttr.in (no API key required by default).
    - text: a natural phrase like "weather in Dublin" (used to guess city)
    - city: explicit city name overrides text parsing
    - fmt: wttr.in format; 'j1' returns JSON
    Returns: {ok, city, url, data?, error?}
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
        base = DEFAULT_WEATHER_URL.rstrip("/")
        path_city = urllib.parse.quote(c)
        url = f"{base}/{path_city}?format={fmt}"
        res = http_get(url)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error") or f"http {res.get('status')}"}
        data = res.get("json") or res.get("text")
        return {"ok": True, "city": c, "url": url, "data": data}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(reg) -> None:
    reg.add("weather.get", weather_get, desc="Fetch weather (wttr.in). Args: text?, city?, fmt='j1'.")
