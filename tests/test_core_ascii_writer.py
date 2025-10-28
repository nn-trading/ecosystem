# Tests for ASCII-safe writer utility (ASCII-01)
import os, sys, json, io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ascii_writer import to_ascii, write_text_ascii, write_jsonl_ascii
from core.pathutil import sanitize_save_path


def test_to_ascii_basic():
    assert to_ascii("naïve ☕") == "nave "
    assert to_ascii("plain ASCII") == "plain ASCII"


def test_write_text_ascii_and_sanitize(tmp_path):
    base = tmp_path / "sub"
    p = str(base / "naïve?.txt")
    out = write_text_ascii(p, "naïve text")
    assert os.path.exists(out)
    assert out.endswith("nave_.txt")
    with open(out, "r", encoding="ascii", errors="ignore") as f:
        assert f.read() == "nave text"


def test_write_jsonl_ascii(tmp_path):
    p = str(tmp_path / "log.jsonl")
    write_jsonl_ascii(p, {"msg": "Café", "ok": True})
    write_jsonl_ascii(p, {"n": 3})
    with open(p, "r", encoding="ascii", errors="ignore") as f:
        lines = f.read().splitlines()
    assert len(lines) == 2
    # Lines must be ASCII-only
    for ln in lines:
        assert all(ord(ch) < 128 for ch in ln)
    # Non-ASCII must be escaped in the first line
    assert ("\\u" in lines[0]) or ("Caf\u00e9" in lines[0]) or ("Caf" in lines[0])
