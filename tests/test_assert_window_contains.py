# C:\bots\ecosys\tests\test_assert_window_contains.py
import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..")))

import importlib

import tools.assertions as A


class _StubReg:
    def __init__(self, ok: bool):
        self._ok = ok
    def call(self, name: str, **kwargs):
        if name == "win.wait_title_contains":
            return {"ok": self._ok}
        return {"ok": False, "error": "unexpected call"}


def test_assert_window_contains_passes_when_wait_ok():
    old = getattr(A, "_TOOLS", None)
    try:
        A._TOOLS = _StubReg(ok=True)
        res = A.assert_window_contains("Notepad", timeout_ms=10)
        assert res.get("ok") is True
        assert res.get("passed") is True
        assert res.get("substr") == "Notepad"
    finally:
        A._TOOLS = old


def test_assert_window_contains_handles_empty_substr():
    old = getattr(A, "_TOOLS", None)
    try:
        A._TOOLS = _StubReg(ok=True)
        res = A.assert_window_contains("", timeout_ms=10)
        assert res.get("ok") is False
        assert "empty substr" in res.get("error", "")
    finally:
        A._TOOLS = old
