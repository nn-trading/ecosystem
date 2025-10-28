# Test weather.get HTTP flow by monkeypatching http_get
import os, sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import weather


def test_weather_get_builds_url_and_returns_json(monkeypatch):
    calls = []
    def fake_http_get(url):
        calls.append(url)
        if url.startswith(weather.DEFAULT_WEATHER_URL.rstrip("/")):
            # respond with JSON-like structure
            return {"ok": True, "json": {"current_condition": [{"temp_C": "12"}]}}
        if url == weather.DEFAULT_IPINFO_URL:
            return {"ok": True, "json": {"city": "Dublin"}}
        return {"ok": False, "status": 404}

    monkeypatch.setattr(weather, "http_get", fake_http_get)
    res = weather.weather_get(city="Paris", fmt="j1")
    assert res.get("ok") is True
    assert res.get("city") == "Paris"
    assert "url" in res and "/Paris?format=j1" in res["url"]
    assert isinstance(res.get("data"), (dict, str))


def test_weather_get_uses_ipinfo_when_no_city(monkeypatch):
    calls = {"ip": 0, "wttr": 0}
    def fake_http_get(url):
        if url == weather.DEFAULT_IPINFO_URL:
            calls["ip"] += 1
            return {"ok": True, "json": {"city": "Tokyo"}}
        if url.startswith(weather.DEFAULT_WEATHER_URL.rstrip("/")):
            calls["wttr"] += 1
            return {"ok": True, "json": {"current_condition": [{"temp_C": "18"}]}}
        return {"ok": False}

    monkeypatch.setattr(weather, "http_get", fake_http_get)
    res = weather.weather_get(text="weather now", fmt="j1")
    assert res.get("ok") is True
    assert res.get("city") == "Tokyo"
    assert calls["ip"] == 1 and calls["wttr"] == 1
