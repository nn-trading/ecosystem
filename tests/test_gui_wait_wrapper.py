from tools.gui_tool import wait_title_contains

def test_gui_wait_wrapper_smoke():
    res = wait_title_contains("Notepad", timeout_sec=1, poll_ms=200)
    assert isinstance(res, dict)
    for k in ("ok", "contains", "title"):
        assert k in res
