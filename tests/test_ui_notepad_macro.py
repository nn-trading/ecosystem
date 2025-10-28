import os, sys
import pytest

# Ensure project import path
sys.path.insert(0, r"C:\bots\ecosys")
from core.tools import REGISTRY


def _norm(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n")


win_and_danger = (os.name == "nt") and (os.environ.get("AGENT_DANGER_MODE", "0") == "1")

@pytest.mark.skipif(not win_and_danger, reason="UI test requires Windows and AGENT_DANGER_MODE=1")
def test_notepad_copy_paste_equality():
    txt = "UI macro test\nline2\nok"

    r1 = REGISTRY.call("macro.notepad_type_copy", text=txt)
    assert r1.get("ok"), r1
    assert _norm(r1.get("text", "")) == _norm(txt)

    r2 = REGISTRY.call("macro.paste_to_new_notepad")
    assert r2.get("ok"), r2
    assert _norm(r2.get("text", "")) == _norm(txt)

    # Best-effort cleanup: close notepad instances
    try:
        REGISTRY.call("shell.run", cmd="taskkill /IM notepad.exe /F", timeout=5)
    except Exception:
        pass
