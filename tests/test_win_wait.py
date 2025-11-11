import json
from core.win_wait import wait_title_contains

def test_win_wait_smoke():
    res = wait_title_contains("Notepad", timeout_sec=1, poll_ms=200)
    assert isinstance(res, dict)
    # must include these keys; ok may be True/False depending on environment
    for k in ("ok", "contains", "title"):
        assert k in res
