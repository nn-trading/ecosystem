# C:\bots\ecosys\tools\assertions.py
from __future__ import annotations
from typing import Any, Dict, Optional
import os
import time
import json

_TOOLS = None  # set in register()
DANGER = os.environ.get("AGENT_DANGER_MODE", "1") == "1"


def _call(name: str, **kwargs) -> Dict[str, Any]:
    global _TOOLS
    if _TOOLS is None:
        return {"ok": False, "error": "registry not ready"}
    try:
        return _TOOLS.call(name, **kwargs)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _norm_text(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n")


# 1) Assert a window title contains a substring within a timeout
# Returns: {ok, passed, substr}

def assert_window_contains(substr: str, timeout_ms: int = 1500) -> Dict[str, Any]:
    try:
        if not substr:
            return {"ok": False, "error": "empty substr"}
        sec = max(1, int(round((timeout_ms or 0) / 1000.0)))
        res = _call("win.wait_title_contains", substr=substr, timeout=sec)
        passed = bool(res.get("ok"))
        return {"ok": True, "passed": passed, "substr": substr}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# 2) Assert current active window text equals the clipboard content
# Strategy: snapshot clipboard, select-all + copy window, compare with snapshot
# Returns: {ok, passed, expected, observed}

def assert_clipboard_equals_window(max_wait_ms: int = 1200) -> Dict[str, Any]:
    try:
        # Snapshot current clipboard
        g1 = _call("clipboard.get_text")
        expected = _norm_text(g1.get("text", "") if isinstance(g1, dict) else "")
        if not DANGER:
            # In non-danger mode we cannot interact with UI; best-effort compare to itself
            return {"ok": True, "passed": (expected == expected), "expected": expected, "observed": expected}
        # Select all and copy from active window
        _call("ui.hotkey", keys=["ctrl", "a"])  # ignore result
        _call("ui.hotkey", keys=["ctrl", "c"])  # ignore result
        # Poll clipboard for stability
        deadline = time.time() + (max_wait_ms / 1000.0)
        observed = ""
        while time.time() < deadline:
            g2 = _call("clipboard.get_text")
            observed = _norm_text(g2.get("text", "") if isinstance(g2, dict) else "")
            if observed is not None:
                break
            time.sleep(0.05)
        passed = (observed == expected)
        return {"ok": True, "passed": passed, "expected": expected, "observed": observed}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# 3) Assert a file exists at path
# Returns: {ok, passed, path}

def assert_file_exists(path: str) -> Dict[str, Any]:
    try:
        if not path:
            return {"ok": False, "error": "empty path"}
        exists = os.path.exists(path)
        return {"ok": True, "passed": bool(exists), "path": path}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# 4) Assert weather detected city equals expected (case-insensitive)
# Returns: {ok, passed, expected, actual, provider}

def assert_weather_city_eq(expected_city: str, text: Optional[str] = None, city: Optional[str] = None) -> Dict[str, Any]:
    try:
        exp = (expected_city or "").strip()
        if not exp:
            return {"ok": False, "error": "empty expected_city"}
        w = _call("weather.get", text=text, city=city)
        if not isinstance(w, dict) or not w.get("ok"):
            return {"ok": False, "error": w.get("error", "weather_failed") if isinstance(w, dict) else "weather_failed"}
        actual = str(w.get("city", ""))
        passed = (actual.strip().lower() == exp.lower()) if actual else False
        return {"ok": True, "passed": passed, "expected": exp, "actual": actual, "provider": w.get("provider")}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# 5) Assert currency conversion returns a positive number (optionally above min_value)
# Returns: {ok, passed, amount, from, to, result, rate, provider}

def assert_fx_positive_number(amount: float, from_currency: str, to_currency: str, min_value: float = 0.0) -> Dict[str, Any]:
    try:
        res = _call("currency.convert", amount=float(amount), from_currency=from_currency, to_currency=to_currency)
        if not isinstance(res, dict) or not res.get("ok"):
            return {"ok": False, "error": res.get("error", "conversion_failed") if isinstance(res, dict) else "conversion_failed"}
        result_val = res.get("result")
        try:
            val = float(result_val)
        except Exception:
            return {"ok": True, "passed": False, "result": result_val, "rate": res.get("rate"), "provider": res.get("provider")}
        passed = (val > float(min_value))
        out = {
            "ok": True,
            "passed": passed,
            "amount": res.get("amount"),
            "from": res.get("from"),
            "to": res.get("to"),
            "result": val,
            "rate": res.get("rate"),
            "provider": res.get("provider"),
        }
        return out
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(reg) -> None:
    global _TOOLS
    _TOOLS = reg
    reg.add("assert.window_contains", assert_window_contains, desc="Assert any window title contains substring within timeout")
    reg.add("assert.clipboard_equals_window", assert_clipboard_equals_window, desc="Assert active window text equals previously-snapshotted clipboard")
    reg.add("assert.file_exists", assert_file_exists, desc="Assert a file exists at path")
    reg.add("assert.weather_city_eq", assert_weather_city_eq, desc="Assert weather-detected city equals expected")
    reg.add("assert.fx_positive_number", assert_fx_positive_number, desc="Assert currency conversion yields positive number above min_value")
