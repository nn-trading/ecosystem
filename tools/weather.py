# C:\bots\ecosys\tools\weather.py
from __future__ import annotations
from typing import Any, Dict
import urllib.request, urllib.parse, json, os, ssl

DANGER = os.environ.get("AGENT_DANGER_MODE", "1") == "1"

def _http_get_json(url: str, timeout: int = 12) -> Dict[str, Any]:
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, context=ctx, timeout=timeout) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    return json.loads(data)

def _wttr(location: str) -> Dict[str, Any]:
    q = urllib.parse.quote(location.strip())
    url = f"https://wttr.in/{q}?format=j1"
    data = _http_get_json(url)
    cur = (data.get("current_condition") or [{}])[0]
    return {
        "ok": True,
        "provider": "wttr",
        "location": location,
        "temp_C": cur.get("temp_C"),
        "feelslike_C": cur.get("FeelsLikeC"),
        "windspeed_kmph": cur.get("windspeedKmph"),
        "humidity": cur.get("humidity"),
        "desc": ((cur.get("weatherDesc") or [{}])[0]).get("value"),
    }

def _open_meteo(location: str) -> Dict[str, Any]:
    # 1) Geocode the name -> lat/lon
    q = urllib.parse.quote(location.strip())
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1"
    geo = _http_get_json(geo_url)
    results = geo.get("results") or []
    if not results:
        return {"ok": False, "error": f"no geocode result for '{location}'"}
    lat = results[0].get("latitude")
    lon = results[0].get("longitude")
    name = results[0].get("name")

    # 2) Current weather
    wx_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current_weather=true"
    )
    data = _http_get_json(wx_url)
    cur = data.get("current_weather") or {}
    if not cur:
        return {"ok": False, "error": "no current_weather from Open-Meteo"}

    # Open-Meteo returns temperature in °C and windspeed in km/h by default.
    return {
        "ok": True,
        "provider": "open-meteo",
        "location": name or location,
        "temp_C": cur.get("temperature"),
        "windspeed_kmph": cur.get("windspeed"),
        "winddirection_deg": cur.get("winddirection"),
        "desc": f"weathercode {cur.get('weathercode')}",
    }

def get(location: str) -> Dict[str, Any]:
    if not DANGER:
        return {"ok": False, "error": "danger_mode off"}
    provider = (os.environ.get("WEATHER_PROVIDER") or "wttr").strip().lower()
    try:
        if provider == "open-meteo":
            return _open_meteo(location)
        # default: wttr.in
        return _wttr(location)
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

def register(tools) -> None:
    tools.add("weather.get", get, desc="Get current weather for a location (provider selectable via WEATHER_PROVIDER)")
