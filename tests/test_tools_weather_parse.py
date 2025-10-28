# Unit tests for weather text parsing (no network)
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.weather import _detect_city_from_text

def test_detect_city_basic():
    assert _detect_city_from_text("what's the weather in Dublin right now?") == "Dublin"
    assert _detect_city_from_text("weather in Tokyo now") == "Tokyo"


def test_detect_city_avoid_for_n_days_tail():
    assert _detect_city_from_text("Show weather in New York for 3 days") == "New York"
    assert _detect_city_from_text("Forecast in San Francisco for 10 days") == "San Francisco"


def test_detect_city_fallback_last_word():
    # When no 'in <city>' present, fallback to last meaningful token
    assert _detect_city_from_text("weather Paris") == "Paris"


def test_detect_city_none_when_no_text():
    assert _detect_city_from_text("") is None
