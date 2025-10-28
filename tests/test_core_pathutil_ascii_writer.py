# Tests for ASCII-safe conversions in pathutil (ASCII-01)
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.pathutil import sanitize_filename, sanitize_save_path


def test_sanitize_filename_ascii_only_and_reserved_names():
    assert sanitize_filename("naïve.txt") == "nave.txt"
    assert sanitize_filename("con") == "_con"
    assert sanitize_filename("LPT1") == "_LPT1"
    assert sanitize_filename("bad<name>.md") == "bad_name_.md"


def test_sanitize_save_path_only_filename_component():
    p, changed = sanitize_save_path("C:/tmp/naïve?.txt")
    assert changed is True
    assert p.endswith("nave_.txt")
