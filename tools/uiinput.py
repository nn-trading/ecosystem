from __future__ import annotations
try:
    import pyautogui
except Exception:
    pyautogui = None

def _need(danger: bool):
    if not danger:
        return {"ok": False, "error": "danger_mode off"}
    if not pyautogui:
        return {"ok": False, "error": "pyautogui not installed"}
    return None

def type_text(text: str, interval: float = 0.0, danger: bool = False) -> dict:
    chk = _need(danger)
    if chk: return chk
    try:
        pyautogui.typewrite(text or "", interval=interval)
        return {"ok": True, "typed": len(text or "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def click(x: int | None = None, y: int | None = None, button: str = "left", danger: bool = False) -> dict:
    chk = _need(danger)
    if chk: return chk
    try:
        if x is not None and y is not None:
            pyautogui.click(x, y, button=button)
        else:
            pyautogui.click(button=button)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def move(x: int, y: int, duration: float = 0.0, danger: bool = False) -> dict:
    chk = _need(danger)
    if chk: return chk
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def hotkey(keys: list[str], danger: bool = False) -> dict:
    chk = _need(danger)
    if chk: return chk
    try:
        if not isinstance(keys, (list, tuple)) or not keys:
            return {"ok": False, "error": "keys must be a non-empty list"}
        pyautogui.hotkey(*keys)
        return {"ok": True, "keys": list(keys)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
