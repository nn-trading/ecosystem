# Tests for weather.get fallback + normalized schema
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import weather


def test_weather_get_normalized_fields_and_provider(monkeypatch):
    calls = []
    def fake_http_get(url):
        calls.append(url)
        if url.startswith(weather.DEFAULT_WEATHER_URL.rstrip("/")):
            return {"ok": True, "json": {"current_condition": [{"temp_C": "7", "weatherDesc": [{"value": "Cloudy"}]}]}}
        if url == weather.DEFAULT_IPINFO_URL:
            return {"ok": True, "json": {"city": "Berlin"}}
        return {"ok": False, "status": 503}

    monkeypatch.setattr(weather, "http_get", fake_http_get)
    res = weather.weather_get(text="weather in Berlin right now", fmt="j1")
    assert res.get("ok") is True
    assert res.get("city") == "Berlin"
    assert res.get("provider")
    norm = res.get("norm") or {}
    assert isinstance(norm, dict)
    assert norm.get("condition") == "Cloudy"
    assert abs(float(norm.get("temp_c", 0)) - 7.0) < 1e-9
